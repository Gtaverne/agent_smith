// Global state object to store DOM elements and other shared data
const state = {
  elements: {},
  currentUrl: ''
};

document.addEventListener("DOMContentLoaded", () => {
  initializeState();
  attachEventListeners();
});

// Initialize the global state with DOM elements
function initializeState() {
  const elementIds = ['getCurrentUrlBtn', 'loader', 'result', 'summaryText', 'articlesList'];
  elementIds.forEach(id => {
    state.elements[id] = document.getElementById(id);
  });

  if (Object.values(state.elements).some(el => !el)) {
    console.error("One or more DOM elements not found");
    return;
  }
}

// Attach event listeners to buttons
function attachEventListeners() {
  state.elements.getCurrentUrlBtn.addEventListener("click", handleGetCurrentUrl);
}

// Handle getting the current URL from the active tab
function handleGetCurrentUrl() {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    if (tabs[0] && tabs[0].url) {
      state.currentUrl = tabs[0].url;
      handleSubmit();
    } else {
      alert("Unable to get the current URL. Please try again.");
    }
  });
}

// Function to handle form submission and API call
async function handleSubmit() {
  if (!state.currentUrl) {
    alert("No URL available. Please click 'Get Current URL' first.");
    return;
  }

  if (!isValidURL(state.currentUrl)) {
    alert("The current URL is not valid.");
    return;
  }

  toggleUIElements(true);

  try {
    const data = await fetchAnalysis(state.currentUrl);
    updateUIWithResult(data);
  } catch (error) {
    console.error("Error:", error);
    alert("An error occurred while processing the request.");
  } finally {
    toggleUIElements(false);
  }
}

// Function to check if the input is a valid URL
function isValidURL(string) {
  try {
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

// Function to make the API call
async function fetchAnalysis(content) {
  const response = await fetch("http://localhost:8000/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content })
  });

  if (!response.ok) {
    throw new Error("Network response was not ok");
  }

  return await response.json();
}

// Function to update UI with analysis results
function updateUIWithResult(data) {
  state.elements.summaryText.textContent = data.summary;
  state.elements.articlesList.innerHTML = "";
  data.articles.forEach(article => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = article;
    a.textContent = article;
    a.target = "_blank";
    li.appendChild(a);
    state.elements.articlesList.appendChild(li);
  });
  state.elements.result.classList.remove("hidden");
}

// Function to toggle UI elements during loading
function toggleUIElements(isLoading) {
  state.elements.loader.classList.toggle("hidden", !isLoading);
  state.elements.getCurrentUrlBtn.disabled = isLoading;
  if (isLoading) {
    state.elements.result.classList.add("hidden");
  }
}
