"""
PathFinding Core Functions
경로 최적화 핵심 함수들 - PathFinding_Final.py에서 복사

Author: AI Development Team
Date: 2024-12-19
"""

import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import networkx as nx
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import GridSearchCV
from sklearn.cluster import KMeans
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import folium

def load_and_project_graph(place_name: str):
    G0 = ox.graph_from_place(place_name, network_type='drive')
    G = ox.project_graph(G0)
    logging.info("그래프 투영 완료 (CRS=%s)", G.graph['crs'])
    return G0, G

def load_and_project_violations(csv_path: str, G_proj: nx.MultiDiGraph, backend_url: str = "http://localhost:8080"):
    # 1. 기존 CSV 데이터 로드
    df_csv = pd.read_csv(csv_path, encoding="cp949").dropna(subset=["위도","경도"])
    logging.info("CSV 데이터 로드 완료: %d개 좌표", len(df_csv))
    
    # 2. 백엔드 DB 데이터 추가 로드
    df_db = pd.DataFrame()
    try:
        import requests
        response = requests.get(f"{backend_url}/api/detections", timeout=10)
        if response.status_code == 200:
            db_data = response.json()
            
            # DB 데이터를 CSV 형식에 맞게 변환
            db_records = []
            for record in db_data:
                if record.get('latitude') and record.get('longitude'):
                    db_records.append({
                        '위도': record['latitude'],
                        '경도': record['longitude'],
                        '위치정보': record.get('location', ''),
                        '단속일시': record.get('detectedAt', ''),
                        '위반심각도': record.get('violationSeverity', 1.0)
                    })
            
            if db_records:
                df_db = pd.DataFrame(db_records)
                logging.info("DB 데이터 로드 완료: %d개 좌표", len(df_db))
            else:
                logging.info("DB에 위반 데이터가 없음")
                
        else:
            logging.warning("DB 접근 실패 (상태코드: %d), CSV만 사용", response.status_code)
            
    except Exception as e:
        logging.warning("DB 접근 오류 (%s), CSV만 사용", str(e))
    
    # 3. 데이터 결합
    if not df_db.empty:
        df_combined = pd.concat([df_csv, df_db], ignore_index=True)
        logging.info("데이터 결합 완료: 총 %d개 좌표 (CSV %d개 + DB %d개)", len(df_combined), len(df_csv), len(df_db))
    else:
        df_combined = df_csv
        logging.info("CSV 데이터만 사용: %d개 좌표", len(df_combined))
    
    # 4. 기존과 동일한 투영 처리
    gdf = gpd.GeoDataFrame(df_combined,
                           geometry=gpd.points_from_xy(df_combined['경도'], df_combined['위도']),
                           crs="EPSG:4326")
    gdf2 = gdf.to_crs(G_proj.graph['crs'])
    coords = np.vstack([gdf2.geometry.x, gdf2.geometry.y]).T
    logging.info("위반 지점 투영 완료: %d개 좌표", len(coords))
    return coords

def fit_kde(coords: np.ndarray, bandwidths: list) -> KernelDensity:
    sample_size = min(len(coords), 10000)
    idx = np.random.default_rng(0).choice(len(coords), sample_size, replace=False)
    sample = coords[idx]
    grid = GridSearchCV(KernelDensity(kernel="gaussian"), {"bandwidth": bandwidths}, cv=3, n_jobs=-1)
    grid.fit(sample)
    logging.info("최적 KDE bandwidth: %.1f", grid.best_params_['bandwidth'])
    return grid.best_estimator_

def map_density_to_nodes(G: nx.MultiDiGraph, kde: KernelDensity):
    nodes = list(G.nodes)
    xy = np.array([(G.nodes[n]['x'], G.nodes[n]['y']) for n in nodes])
    log_d = kde.score_samples(xy)
    dens = np.exp(log_d)
    for n, w in zip(nodes, dens):
        G.nodes[n]['density_weight'] = w
    logging.info("노드 밀도 매핑 완료")
    return nodes, dens

def select_top_nodes_with_spacing(
    nodes: list,
    dens: np.ndarray,
    ratio: float,
    min_count: int,
    G: nx.MultiDiGraph,
    min_spacing_m: float = 500.0
) -> list:
    order = np.argsort(dens)[::-1]
    total = dens.sum()
    cum = 0
    selected = []
    coords = {n: (G.nodes[n]['x'], G.nodes[n]['y']) for n in nodes}

    def far_enough(candidate):
        cx, cy = coords[candidate]
        for s in selected:
            sx, sy = coords[s]
            if np.hypot(cx - sx, cy - sy) < min_spacing_m:
                return False
        return True

    for idx in order:
        node = nodes[idx]
        if far_enough(node):
            selected.append(node)
            cum += dens[idx]
            if cum / total >= ratio and len(selected) >= min_count:
                break
    if len(selected) < min_count:
        for idx in order:
            node = nodes[idx]
            if node not in selected and far_enough(node):
                selected.append(node)
                if len(selected) >= min_count:
                    break
    logging.info("간격 적용 후 선택된 노드: %d개", len(selected))
    return selected

def compute_distance_matrix(G: nx.MultiDiGraph, selected: list) -> np.ndarray:
    n = len(selected)
    D = np.full((n, n), 10**9, dtype=int)
    for i, u in enumerate(selected):
        for j, v in enumerate(selected):
            if i == j: continue
            try:
                D[i, j] = int(nx.shortest_path_length(G, u, v, weight='length'))
            except nx.NetworkXNoPath:
                pass
    logging.info("거리 행렬 계산 완료")
    return D

def compute_penalties(G: nx.MultiDiGraph, selected: list, D: np.ndarray, factor: float) -> list:
    dens = np.array([G.nodes[n]['density_weight'] for n in selected])
    norm = (dens - dens.min()) / (dens.max() - dens.min()) if dens.max() > dens.min() else np.zeros_like(dens)
    avg = D[D < 10**9].mean()
    base = avg * factor
    penalties = (norm * base).astype(int).tolist()
    logging.info("페널티 계산 완료 (base_pen=%.1f)", base)
    return penalties

def solve_vrp(D: list, penalties: list, num_vehicles: int, depot: int, time_limit_s: int):
    mgr = pywrapcp.RoutingIndexManager(len(D), num_vehicles, depot)
    routing = pywrapcp.RoutingModel(mgr)
    def dist_cb(i, j):
        return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
    tidx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(tidx)
    for idx, p in enumerate(penalties):
        if idx == depot: continue
        routing.AddDisjunction([mgr.NodeToIndex(idx)], p)
    from math import ceil
    n = len(D)
    demands = [1]*n
    cap = ceil(n/num_vehicles)
    caps = [cap]*num_vehicles
    def demand_cb(i): return demands[mgr.IndexToNode(i)]
    didx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(didx, 0, caps, True, 'Capacity')
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.time_limit.seconds = time_limit_s
    sol = routing.SolveWithParameters(params)
    if sol: logging.info("VRP 솔루션 발견")
    else: logging.error("VRP 솔루션 없음")
    return mgr, routing, sol

def visualize_clustered_routes(
    G0: nx.MultiDiGraph,
    routes: dict,
    place_name: str,
    start_lat: float,
    start_lon: float,
    save_path: str = 'clustered_routes.html'
):
    m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    folium.Marker([start_lat, start_lon], tooltip='Start/Depot', 
                  icon=folium.Icon(color='black', icon='home')).add_to(m)
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'cadetblue']
    for vidx, (veh, node_list) in enumerate(routes.items()):
        coords = [(G0.nodes[n]['y'], G0.nodes[n]['x']) for n in node_list]
        if len(coords) == 1:
            coords = coords * 2
        folium.PolyLine(coords, color=colors[vidx%len(colors)], weight=5, opacity=0.8,
                        tooltip=f'차량 {veh+1}').add_to(m)
    # 범례
    legend_items = ''.join([
        f"<i style='background:{colors[i]};width:10px;height:10px;display:inline-block;margin-right:5px;'></i>"
        f"차량 {i+1}<br>" for i in routes.keys()
    ])
    legend_html = f"""
     <div style="position: absolute; bottom: 50px; left: 50px; background-color: white; 
                  border:2px solid grey; z-index:9999; font-size:14px; padding:10px;">
       <b>차량 경로 색상</b><br>{legend_items}
     </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    m.save(save_path)
    logging.info("지도 저장: %s", save_path)
    return save_path

def extract_vehicle_routes(manager, routing, sol, selected):
    """솔루션에서 각 차량별 방문 노드 리스트(node IDs) 리턴"""
    routes = {}
    for veh in range(routing.vehicles()):
        idx = routing.Start(veh)
        route = []
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            route.append(selected[node])
            idx = sol.Value(routing.NextVar(idx))
        # 마지막 디포 추가
        route.append(selected[manager.IndexToNode(idx)])
        routes[veh] = route
    return routes

def run_clustered_vrp(
    place_name: str = "Seocho-gu, Seoul, South Korea",
    csv_path: str = "../Data/CCTV기반단속개별건수.csv",
    num_vehicles: int = 3,
    coverage_ratio: float = 0.7,
    min_nodes: int = 50,
    bandwidths: list = (50,100,150,200),
    penalty_factor: float = 5.0,
    min_spacing: float = 500.0,
    time_limit: int = 120,
    start_lat: float = 37.4835,
    start_lon: float = 127.0322,
    backend_url: str = "http://localhost:8080",
):
    G0, G = load_and_project_graph(place_name)
    xy = load_and_project_violations(csv_path, G, backend_url)
    kde = fit_kde(xy, bandwidths)
    nodes, dens = map_density_to_nodes(G, kde)
    selected = select_top_nodes_with_spacing(nodes, dens, coverage_ratio, min_nodes, G, min_spacing)
    pt = gpd.GeoSeries([Point(start_lon, start_lat)], crs='EPSG:4326').to_crs(G.graph['crs'])
    sx, sy = pt.geometry.x[0], pt.geometry.y[0]
    start_node = ox.nearest_nodes(G, sx, sy)
    if start_node not in selected: selected.insert(0, start_node)
    coords = np.array([(G.nodes[n]['x'], G.nodes[n]['y']) for n in selected])
    km = KMeans(n_clusters=num_vehicles, random_state=0).fit(coords)
    clusters = {i: [] for i in range(num_vehicles)}
    for n, lbl in zip(selected, km.labels_): clusters[lbl].append(n)
    routes = {}
    for v in range(num_vehicles):
        sel = clusters[v]
        if start_node not in sel: sel.insert(0, start_node)
        D = compute_distance_matrix(G, sel)
        pens = compute_penalties(G, sel, D, penalty_factor)
        mgr, routing, sol = solve_vrp(D.tolist(), pens, 1, 0, time_limit)
        rv = {} if not sol else extract_vehicle_routes(mgr, routing, sol, sel)
        routes[v] = rv.get(0, [])
    # 시각화
    map_file = visualize_clustered_routes(G0, routes, place_name, start_lat, start_lon, save_path="".join(["optimized_routes_", str(num_vehicles), ".html"]))
    return routes, map_file, G0
