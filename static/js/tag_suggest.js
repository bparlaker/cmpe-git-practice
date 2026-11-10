// Tag suggestions while typing (US-06, FR-4.3).
// I look at the last tag after the last comma, ask the server for tags that
// start with it, and show them as buttons. A click replaces the half typed tag.

const tagInput = document.getElementById("id_tags");
const suggestionBox = document.getElementById("tag-suggestions");

function lastTag() {
  const parts = tagInput.value.split(",");
  return parts[parts.length - 1].trim();
}

function useSuggestion(name) {
  const parts = tagInput.value.split(",");
  parts[parts.length - 1] = " " + name;
  tagInput.value = parts.join(",").trim() + ", ";
  suggestionBox.innerHTML = "";
  tagInput.focus();
}

let waitTimer = null;

tagInput.addEventListener("input", function () {
  // I wait 250 ms after the last key, so I do not call the server for every letter.
  clearTimeout(waitTimer);
  waitTimer = setTimeout(function () {
    const text = lastTag();
    if (text.length < 2) {
      suggestionBox.innerHTML = "";
      return;
    }
    fetch(suggestionBox.dataset.url + "?q=" + encodeURIComponent(text))
      .then((response) => response.json())
      .then((data) => {
        suggestionBox.innerHTML = "";
        data.tags.forEach(function (tag) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "btn btn-sm btn-light border me-1 mb-1";
          button.textContent = tag.name + " (" + tag.count + " entries)";
          button.addEventListener("click", function () {
            useSuggestion(tag.name);
          });
          suggestionBox.appendChild(button);
        });
      });
  }, 250);
});
