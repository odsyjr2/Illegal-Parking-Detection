import MapPage from './MapPage'
import InfoPanel from './InfoPanel'
import './MainPage.css'
import { useState } from 'react'

function MainPage() {
  const [selectedLocation, setSelectedLocation] = useState(null)

  return (
    <div className="main-layout">
      <div className="main-map">
        <MapPage
          selectedLocation={selectedLocation}
          onLocationChange={setSelectedLocation}
        />
      </div>
      <div className="side-panel">
        <InfoPanel
          selectedLocation={selectedLocation}
          onLocationChange={setSelectedLocation}
        />
      </div>
    </div>
  )
}

export default MainPage
