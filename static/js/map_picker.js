// The map on the "add entry" form (FR-5.1).
// A click on the map, or a place search, puts a pin and fills the hidden
// latitude and longitude fields of the form.

const latInput = document.getElementById("id_latitude");
const lngInput = document.getElementById("id_longitude");
const placeInput = document.getElementById("id_place_name");

// I start with the whole of Turkey on the screen.
const map = L.map("map").setView([39.0, 35.0], 5);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let marker = null;

function putPin(lat, lng) {
  if (marker) {
    marker.setLatLng([lat, lng]);
  } else {
    marker = L.marker([lat, lng]).addTo(map);
  }
  // 5 decimals is about 1 meter, more than enough for a place.
  latInput.value = lat.toFixed(5);
  lngInput.value = lng.toFixed(5);
}

// When the form comes back with an error, or when editing, the pin is
// already known, so I show it again.
if (latInput.value && lngInput.value) {
  putPin(parseFloat(latInput.value), parseFloat(lngInput.value));
  map.setView([parseFloat(latInput.value), parseFloat(lngInput.value)], 8);
}

map.on("click", function (event) {
  putPin(event.latlng.lat, event.latlng.lng);
});

// Place search with OpenStreetMap's free Nominatim service.
const searchInput = document.getElementById("place-search");
const searchButton = document.getElementById("place-search-button");

function searchPlace() {
  const text = searchInput.value.trim();
  if (!text) {
    return;
  }
  const url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(text);
  fetch(url)
    .then((response) => response.json())
    .then((results) => {
      if (results.length === 0) {
        alert("I could not find this place. Try another name or click on the map.");
        return;
      }
      const lat = parseFloat(results[0].lat);
      const lng = parseFloat(results[0].lon);
      putPin(lat, lng);
      map.setView([lat, lng], 9);
      // I fill the place name only if the user has not written one.
      if (!placeInput.value) {
        placeInput.value = text;
      }
    });
}

searchButton.addEventListener("click", searchPlace);
// Pressing Enter in the search box should search, not submit the whole form.
searchInput.addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    event.preventDefault();
    searchPlace();
  }
});
