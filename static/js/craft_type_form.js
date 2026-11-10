// While the user types a craft type name, I show existing names that are
// almost the same (FR-2.5), for example "Kilm" -> "Kilim".
// The server also checks this when the form is saved.

const nameInput = document.getElementById("id_name");
const similarBox = document.getElementById("similar-types");
let typingTimer = null;

nameInput.addEventListener("input", function () {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(function () {
    const name = nameInput.value.trim();
    if (name.length < 3) {
      similarBox.textContent = "";
      return;
    }
    fetch(similarBox.dataset.url + "?name=" + encodeURIComponent(name))
      .then((response) => response.json())
      .then((data) => {
        if (data.similar.length > 0) {
          similarBox.textContent = "Similar types already exist: " + data.similar.join(", ") + ". Maybe use one of them?";
        } else {
          similarBox.textContent = "";
        }
      });
  }, 300);
});
