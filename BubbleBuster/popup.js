document.addEventListener("DOMContentLoaded", () => {
    const articleContentEl = document.getElementById("articleContent");
    const submitBtn = document.getElementById("submitBtn");
    const loaderEl = document.getElementById("loader");
    const resultEl = document.getElementById("result");
    const summaryTextEl = document.getElementById("summaryText");
    const articlesListEl = document.getElementById("articlesList");
  
    submitBtn.addEventListener("click", async () => {
      const content = articleContentEl.value.trim();
      if (!content) {
        alert("Please enter the article text.");
        return;
      }
  
      // Show loader and disable the button
      loaderEl.classList.remove("hidden");
      submitBtn.disabled = true;
      resultEl.classList.add("hidden");
  
      try {
        const response = await fetch("http://localhost:8000/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ content })
        });
  
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
  
        const data = await response.json();
  
        // Update the UI with the analysis result
        summaryTextEl.textContent = data.summary;
        articlesListEl.innerHTML = "";
        data.articles.forEach(article => {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = article;
          a.textContent = article;
          a.target = "_blank";
          li.appendChild(a);
          articlesListEl.appendChild(li);
        });
  
        resultEl.classList.remove("hidden");
      } catch (error) {
        console.error("Error:", error);
        alert("An error occurred while processing the request.");
      } finally {
        loaderEl.classList.add("hidden");
        submitBtn.disabled = false;
      }
    });
  });
  