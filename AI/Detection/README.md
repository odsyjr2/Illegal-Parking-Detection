# 원본 데이터셋 커스텀 변환 가이드

이 문서는 원본 불법주정차 AI 데이터셋을 딥러닝 모델 학습에 적합한 구조로 변환하는 절차를 안내합니다.
`dataset_restruction.py` 스크립트를 사용하여 이미지와 어노테이션 파일을 `train` 및 `valid` 세트로 자동 정리할 수 있습니다.

---

## 🛠️ 사전 준비

1.  **Python 환경**: 스크립트 실행을 위해 Python 3.x 버전이 필요합니다.
2.  **필수 라이브러리 설치**:
    ```bash
    pip install tqdm
    ```

---

## 📁 데이터셋 구조

### 원본 데이터 구조 (예시)

스크립트는 아래와 같은 원본 데이터셋 구조를 가정합니다.

```
138.종합 민원 이미지 AI데이터/
└── 01.데이터/
    ├── 1.Training/
    │   ├── 라벨링데이터/TL3/불법주정차/...
    │   └── 원천데이터/TS3/불법주정차/...
    └── 2.Validation/
        ├── 라벨링데이터/VL3/불법주정차/...
        └── 원천데이터/VS3/불법주정차/...
```

### 변환 후 데이터 구조

스크립트 실행 시, 다음과 같이 `custom_dataset` 폴더가 생성됩니다.

```
custom_dataset/
├── train/
│   ├── images/
│   └── annotations/
└── valid/
    ├── images/
    └── annotations/
```

---

## ⚙️ 변환 절차

1.  **스크립트 실행**

    `AI/Detection` 폴더에서 아래 명령어를 실행하여 데이터 변환을 시작합니다.

    ```bash
    python dataset_restruction.py
    ```

2.  **경로 지정 (선택 사항)**

    기본 경로가 아닌 다른 위치의 데이터를 변환하려면 `--src` (원본) 및 `--dst` (타겟) 인자를 사용합니다.

    ```bash
    python dataset_restruction.py --src "/path/to/your/data" --dst "/path/to/custom_dataset"
    ```

3.  **실행 완료**

    변환이 완료되면 터미널에 정리된 경로가 출력됩니다.

---

## 💡 추가 정보

-   변환된 데이터셋은 COCO, YOLO 등 다양한 딥러닝 포맷으로 추가 가공하여 활용할 수 있습니다.
-   스크립트의 `main` 함수 내 `parser` 부분을 수정하여 기본 경로 등 설정을 변경할 수 있습니다.

---

## 🚀 YOLOv8 Fine-tuning

fine_tuning_baseline.ipynb에서 `custom_dataset`을 사용하여 YOLOv8 모델을 파인튜닝하는 과정을 안내합니다.



## 변경 사항
data.yaml -> original_cctv_dataset.yaml

line detection filter annotation : 미완성