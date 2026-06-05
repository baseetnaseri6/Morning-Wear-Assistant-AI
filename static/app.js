let currentRecommendation = "";
let currentRecommendationObject = null;
let currentClosetItems = [];

document.addEventListener("DOMContentLoaded", async () => {
    initTheme();
    setDefaultImageVisual();
    await loadWeatherOnStart();
    await loadCloset();
    await loadFavorites();
});

function initTheme() {
    const savedTheme = localStorage.getItem("theme") || "light";
    const body = document.body;
    const icon = document.getElementById("themeIcon");

    if (savedTheme === "dark") {
        body.classList.add("dark-mode");
        icon.className = "fa-solid fa-sun";
    } else {
        body.classList.remove("dark-mode");
        icon.className = "fa-solid fa-moon";
    }

    document.getElementById("themeToggle").addEventListener("click", () => {
        body.classList.toggle("dark-mode");

        if (body.classList.contains("dark-mode")) {
            localStorage.setItem("theme", "dark");
            icon.className = "fa-solid fa-sun";
            showToast("Dark mode enabled", "info");
        } else {
            localStorage.setItem("theme", "light");
            icon.className = "fa-solid fa-moon";
            showToast("Light mode enabled", "info");
        }
    });
}

function showToast(message, type = "success") {
    const box = document.getElementById("toastBox");
    const toast = document.createElement("div");

    toast.className = `toast-msg ${type}`;

    let icon = "fa-circle-check";
    if (type === "error") icon = "fa-circle-exclamation";
    if (type === "info") icon = "fa-circle-info";

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> ${escapeHtml(message)}`;
    box.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(text) {
    if (!text) return "";

    return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function loadWeatherOnStart() {
    const city = document.getElementById("cityInput").value || "Vechta";
    const country = document.getElementById("countryInput").value || "DE";

    try {
        const response = await fetch(`/api/weather?city=${city}&country=${country}`);
        const data = await response.json();

        if (!data.success) {
            showToast("Weather could not load", "error");
            return;
        }

        updateWeatherBox(data.weather);

    } catch (error) {
        console.error(error);
        showToast("Weather loading failed", "error");
    }
}

function updateWeatherBox(weather) {
    document.getElementById("weatherBox").innerHTML = `
        <h2>${weather.temperature}°C</h2>
        <p>${weather.condition}</p>

        <div class="weather-stats">
            <span>Feels like<br><b>${weather.feels_like}°C</b></span>
            <span>Humidity<br><b>${weather.humidity}%</b></span>
            <span>Wind<br><b>${weather.wind_speed} m/s</b></span>
            <span>Rain<br><b>${weather.rain || 0}%</b></span>
        </div>
    `;
}

function setDefaultImageVisual() {
    const preview = document.getElementById("outfitImagePreview");

    if (!preview) return;

    preview.innerHTML = `
        <div class="real-image-empty">
            <div class="empty-image-icon">
                <i class="fa-solid fa-images"></i>
            </div>
            <strong>Your outfit photos will appear here</strong>
            <p>Add clothing images to your closet, then generate an outfit.</p>
        </div>
    `;
}

function findClosetItemByName(name) {
    if (!name) return null;

    const wanted = String(name).trim().toLowerCase();

    return currentClosetItems.find(item => {
        const itemName = String(item.name || "").trim().toLowerCase();
        return itemName === wanted || wanted.includes(itemName) || itemName.includes(wanted);
    }) || null;
}

function categoryFallback(categoryList) {
    return currentClosetItems.find(item => {
        const cat = String(item.category || "").toLowerCase();
        return categoryList.includes(cat);
    }) || null;
}

function getOutfitPhotoItems(recommendation) {
    const outfit = recommendation.outfit || {};

    const top = findClosetItemByName(outfit.top) || categoryFallback(["top"]);
    const bottom = findClosetItemByName(outfit.bottom) || categoryFallback(["bottom"]);
    const shoes = findClosetItemByName(outfit.shoes) || categoryFallback(["shoes"]);
    const extra = findClosetItemByName(outfit.extra) || categoryFallback(["outerwear", "accessory"]);

    return [
        {
            label: "Top",
            name: outfit.top || top?.name || "Top",
            item: top,
            icon: "fa-solid fa-shirt"
        },
        {
            label: "Bottom",
            name: outfit.bottom || bottom?.name || "Bottom",
            item: bottom,
            icon: "fa-solid fa-user-tie"
        },
        {
            label: "Shoes",
            name: outfit.shoes || shoes?.name || "Shoes",
            item: shoes,
            icon: "fa-solid fa-shoe-prints"
        },
        {
            label: "Extra",
            name: outfit.extra || extra?.name || "Extra",
            item: extra,
            icon: "fa-solid fa-umbrella"
        }
    ];
}

async function updateOutfitVisual(recommendation) {
    const preview = document.getElementById("outfitImagePreview");

    if (!preview) return;

    const photoItems = getOutfitPhotoItems(recommendation);

    preview.innerHTML = `
        <div class="closet-photo-outfit-grid">
            ${photoItems.map(photo => {
                const imagePath = photo.item?.image_path || "";

                if (imagePath) {
                    return `
                        <div class="closet-photo-piece">
                            <div class="closet-photo-img">
                                <img src="${escapeHtml(imagePath)}" alt="${escapeHtml(photo.name)}">
                            </div>
                            <span>${escapeHtml(photo.label)}</span>
                            <strong>${escapeHtml(photo.name)}</strong>
                        </div>
                    `;
                }

                return `
                    <div class="closet-photo-piece missing-photo">
                        <div class="closet-photo-img">
                            <i class="${photo.icon}"></i>
                        </div>
                        <span>${escapeHtml(photo.label)}</span>
                        <strong>${escapeHtml(photo.name)}</strong>
                        <small>No photo</small>
                    </div>
                `;
            }).join("")}
        </div>
    `;
}

function scrollToDashboard() {
    document.getElementById("dashboardArea").scrollIntoView({ behavior: "smooth" });
}

function openClosetModal() {
    loadClosetModal();
    new bootstrap.Modal(document.getElementById("closetModal")).show();
}

function openGeneratorModal() {
    new bootstrap.Modal(document.getElementById("generatorModal")).show();
}

async function generateFromModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById("generatorModal"));
    if (modal) modal.hide();

    await getRecommendation();

    document.querySelector(".recommendation-pro").scrollIntoView({ behavior: "smooth" });
}

function setOccasion(value) {
    const occasionField = document.getElementById("itemOccasion");
    if (occasionField) occasionField.value = value;
}

function itemIcon(category) {
    const icons = {
        top: "fa-solid fa-shirt",
        bottom: "fa-solid fa-user-tie",
        shoes: "fa-solid fa-shoe-prints",
        accessory: "fa-solid fa-clock",
        outerwear: "fa-solid fa-vest"
    };

    return icons[category] || "fa-solid fa-shirt";
}

function buildRecommendationText(recommendation) {
    if (!recommendation || typeof recommendation !== "object") {
        return String(recommendation || "");
    }

    if (recommendation.readable_text) return recommendation.readable_text;

    const outfit = recommendation.outfit || {};
    const reasons = recommendation.reasoning || [];

    return `
Outfit:
- Top: ${outfit.top || "No suitable item found"}
- Bottom: ${outfit.bottom || "No suitable item found"}
- Shoes: ${outfit.shoes || "No suitable item found"}
- Accessories/Outerwear: ${outfit.extra || "No suitable item found"}

Reason:
${reasons.map(reason => "- " + reason).join("\n")}

Extra tip:
${recommendation.advice || ""}
    `.trim();
}

function updateScores(recommendation) {
    const scores = recommendation.scores || { comfort: 8, style: 8, weather: 8 };

    document.querySelector(".rating-cards").innerHTML = `
        <div>
            <i class="fa-solid fa-shield-heart"></i>
            <span>Comfort</span>
            <strong>${scores.comfort || 8}/10</strong>
        </div>

        <div>
            <i class="fa-solid fa-user-check"></i>
            <span>Style</span>
            <strong>${scores.style || 8}/10</strong>
        </div>

        <div>
            <i class="fa-solid fa-cloud-sun"></i>
            <span>Weather</span>
            <strong>${scores.weather || 8}/10</strong>
        </div>
    `;
}

function updateWhyPanel(recommendation) {
    const reasoning = recommendation.reasoning || [];
    const whyPanel = document.querySelector(".why-panel");

    let html = `<h5>Why this outfit?</h5>`;

    reasoning.forEach(reason => {
        html += `
            <div class="why-item">
                <i class="fa-solid fa-check"></i>
                <span>${escapeHtml(reason)}</span>
            </div>
        `;
    });

    if (recommendation.advice) {
        html += `
            <div class="why-item advice-item">
                <i class="fa-solid fa-lightbulb"></i>
                <span>${escapeHtml(recommendation.advice)}</span>
            </div>
        `;
    }

    whyPanel.innerHTML = html;
}

async function updateRecommendationUI(recommendation) {
    const text = buildRecommendationText(recommendation);

    currentRecommendation = text;
    currentRecommendationObject = recommendation;

    document.getElementById("recommendationBox").textContent = text;

    updateScores(recommendation);
    updateWhyPanel(recommendation);

    const titleElement = document.querySelector(".recommendation-content h4");

    if (titleElement && recommendation.title) {
        titleElement.textContent = recommendation.title;
    }

    await updateOutfitVisual(recommendation);
}

async function getRecommendation() {
    const city = document.getElementById("cityInput").value || "Vechta";
    const country = document.getElementById("countryInput").value || "DE";

    document.getElementById("recommendationBox").textContent = "Generating your outfit...";
    showToast("Generating outfit...", "info");

    try {
        const response = await fetch("/api/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city, country })
        });

        const data = await response.json();

        if (!data.success) {
            document.getElementById("recommendationBox").textContent = data.error;
            showToast(data.error || "Recommendation failed", "error");
            return;
        }

        if (Array.isArray(data.closet_items)) {
            currentClosetItems = data.closet_items;
        }

        await updateRecommendationUI(data.recommendation);
        updateWeatherBox(data.weather);

        let eventsHtml = "";

        data.events.forEach(event => {
            eventsHtml += `
                <div class="event-item">
                    <b>${escapeHtml(event.time)}</b>
                    <span>
                        ${escapeHtml(event.title)}
                        <small><i class="fa-solid fa-circle-dot"></i> ${escapeHtml(event.type || "event")}</small>
                    </span>
                </div>
            `;
        });

        document.getElementById("calendarBox").innerHTML = eventsHtml;

        showToast("Outfit generated successfully", "success");

    } catch (error) {
        console.error(error);
        document.getElementById("recommendationBox").textContent = "Something went wrong.";
        showToast("Error generating recommendation", "error");
    }
}

async function addClothingItem() {
    const season = document.getElementById("itemSeason").value;
    const occasion = document.getElementById("itemOccasion").value;
    const notes = document.getElementById("itemNotes").value.trim();
    const imageInput = document.getElementById("itemImage");

    const extraNotes = [
        notes ? `Notes: ${notes}` : "",
        season ? `Season: ${season}` : "",
        occasion ? `Occasion: ${occasion}` : ""
    ].filter(Boolean).join(" | ");

    const name = document.getElementById("itemName").value.trim();

    if (!name) {
        showToast("Please enter item name", "error");
        return;
    }

    const formData = new FormData();
    formData.append("name", name);
    formData.append("category", document.getElementById("itemCategory").value);
    formData.append("color", document.getElementById("itemColor").value.trim());
    formData.append("warmth_level", document.getElementById("warmthLevel").value);
    formData.append("formal_level", document.getElementById("formalLevel").value);
    formData.append("waterproof", document.getElementById("waterproof").value);
    formData.append("notes", extraNotes);

    if (imageInput && imageInput.files.length > 0) {
        formData.append("image", imageInput.files[0]);
    }

    try {
        const response = await fetch("/api/closet", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!data.success) {
            showToast(data.error, "error");
            return;
        }

        resetItemForm();

        const modal = bootstrap.Modal.getInstance(document.getElementById("addItemModal"));
        if (modal) modal.hide();

        await loadCloset();
        await loadClosetModal();

        showToast("Clothing item added", "success");

    } catch (error) {
        console.error(error);
        showToast("Failed to add item", "error");
    }
}

function resetItemForm() {
    document.getElementById("itemName").value = "";
    document.getElementById("itemColor").value = "";
    document.getElementById("itemNotes").value = "";
    document.getElementById("warmthLevel").value = "2";
    document.getElementById("formalLevel").value = "1";
    document.getElementById("waterproof").value = "0";
    document.getElementById("itemSeason").value = "";
    document.getElementById("itemOccasion").value = "";

    const imageInput = document.getElementById("itemImage");
    if (imageInput) imageInput.value = "";
}

function buildClosetCard(item) {
    const imagePath = item.image_path || "";

    return `
        <div class="closet-card">
            <button class="delete-btn" onclick="deleteItem(${item.id})">
                <i class="fa-solid fa-xmark"></i>
            </button>

            <div class="item-icon ${imagePath ? "has-image" : ""}">
                ${
                    imagePath
                        ? `<img src="${escapeHtml(imagePath)}" alt="${escapeHtml(item.name)}">`
                        : `<i class="${itemIcon(item.category)}"></i>`
                }
            </div>

            <h5>${escapeHtml(item.name)}</h5>
            <p>${escapeHtml(item.category)}</p>
            <p>${escapeHtml(item.color || "No color")}</p>
        </div>
    `;
}

async function loadCloset() {
    try {
        const response = await fetch("/api/closet");
        const data = await response.json();

        if (!data.success) return;

        currentClosetItems = data.items;

        document.getElementById("closetCount").textContent = `${data.items.length} items`;

        let html = "";

        if (data.items.length === 0) {
            html = `
                <div class="favorite-item">
                    <div class="favorite-item-content">
                        <div class="favorite-icon">
                            <i class="fa-solid fa-shirt"></i>
                        </div>
                        <div>
                            <strong>No clothing items yet</strong>
                            <p>Click Add Item to build your closet</p>
                        </div>
                    </div>
                </div>
            `;
        }

        data.items.forEach(item => html += buildClosetCard(item));

        document.getElementById("closetBox").innerHTML = html;

    } catch (error) {
        console.error(error);
    }
}

async function loadClosetModal() {
    const box = document.getElementById("closetModalBox");
    if (!box) return;

    const response = await fetch("/api/closet");
    const data = await response.json();

    let html = "";

    if (!data.success || data.items.length === 0) {
        html = `
            <div class="empty-favorites-state">
                <i class="fa-solid fa-shirt"></i>
                <h4>Your closet is empty</h4>
                <p>Add clothes with photos so AI can recommend outfits.</p>
            </div>
        `;
    } else {
        currentClosetItems = data.items;
        data.items.forEach(item => html += buildClosetCard(item));
    }

    box.innerHTML = html;
}

async function deleteItem(id) {
    const response = await fetch(`/api/closet/${id}`, { method: "DELETE" });
    const data = await response.json();

    if (!data.success) {
        showToast(data.error || "Delete failed", "error");
        return;
    }

    await loadCloset();
    await loadClosetModal();

    showToast("Item deleted", "success");
}

async function saveFavorite() {
    if (!currentRecommendation) {
        currentRecommendation = document.getElementById("recommendationBox").textContent;
    }

    if (!currentRecommendation || currentRecommendation.includes("Add clothes")) {
        showToast("Generate recommendation first", "error");
        return;
    }

    const response = await fetch("/api/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            title: currentRecommendationObject?.title || "AI Recommended Outfit",
            outfit_text: currentRecommendation
        })
    });

    const data = await response.json();

    if (data.success && data.duplicate) {
        showToast("This outfit is already saved", "info");
        return;
    }

    if (data.success) {
        await loadFavorites();
        showToast("Saved to favorites", "success");
    } else {
        showToast(data.error || "Save failed", "error");
    }
}

async function loadFavorites() {
    const response = await fetch("/api/favorites");
    const data = await response.json();

    if (!data.success) return;

    let html = "";

    if (data.favorites.length === 0) {
        html = `
            <div class="favorite-item">
                <div class="favorite-item-content">
                    <div class="favorite-icon">
                        <i class="fa-regular fa-heart"></i>
                    </div>
                    <div>
                        <strong>No favorites yet</strong>
                        <p>Saved outfits will appear here</p>
                    </div>
                </div>
            </div>
        `;
    }

    data.favorites.slice(0, 3).forEach(item => {
        html += `
            <div class="favorite-item">
                <div class="favorite-item-content">
                    <div class="favorite-icon">
                        <i class="fa-solid fa-heart"></i>
                    </div>
                    <div>
                        <strong>${escapeHtml(item.title)}</strong>
                        <p>${escapeHtml(item.outfit_text.substring(0, 80))}...</p>
                    </div>
                </div>

                <button class="delete-btn" onclick="deleteFavorite(${item.id})">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
        `;
    });

    document.getElementById("favoritesBox").innerHTML = html;
}

async function openAllFavoritesModal() {
    await refreshFavoritesModalContent();

    const modal = new bootstrap.Modal(document.getElementById("allFavoritesModal"));
    modal.show();
}

async function refreshFavoritesModalContent() {
    const response = await fetch("/api/favorites");
    const data = await response.json();

    let html = "";

    if (!data.success || data.favorites.length === 0) {
        html = `
            <div class="empty-favorites-state">
                <i class="fa-regular fa-heart"></i>
                <h4>No favorite outfits yet</h4>
                <p>Generate an outfit and save it to see it here.</p>
            </div>
        `;
    } else {
        data.favorites.forEach(item => {
            const safeText = escapeBackticks(item.outfit_text);

            html += `
                <div class="all-favorite-card">
                    <div class="all-favorite-card-header">
                        <div class="all-favorite-card-icon">
                            <i class="fa-solid fa-heart"></i>
                        </div>
                        <div>
                            <h4>${escapeHtml(item.title)}</h4>
                            <small>${escapeHtml(item.created_at || "Saved outfit")}</small>
                        </div>
                    </div>

                    <pre>${escapeHtml(item.outfit_text)}</pre>

                    <div class="all-favorite-actions">
                        <button class="use-outfit-btn" onclick="useFavoriteOutfit(\`${safeText}\`)">
                            <i class="fa-solid fa-wand-magic-sparkles"></i>
                            Use Outfit
                        </button>

                        <button class="delete-outfit-btn" onclick="deleteFavorite(${item.id})">
                            <i class="fa-solid fa-trash"></i>
                            Delete
                        </button>
                    </div>
                </div>
            `;
        });
    }

    document.getElementById("allFavoritesBox").innerHTML = html;
}

function escapeBackticks(text) {
    return String(text || "")
        .replace(/\\/g, "\\\\")
        .replace(/`/g, "\\`")
        .replace(/\$/g, "\\$");
}

function useFavoriteOutfit(text) {
    currentRecommendation = text;
    document.getElementById("recommendationBox").textContent = text;

    const modal = bootstrap.Modal.getInstance(document.getElementById("allFavoritesModal"));
    if (modal) modal.hide();

    document.querySelector(".recommendation-pro").scrollIntoView({ behavior: "smooth" });

    showToast("Favorite outfit loaded", "success");
}

async function deleteFavorite(id) {
    const response = await fetch(`/api/favorites/${id}`, { method: "DELETE" });
    const data = await response.json();

    if (!data.success) {
        showToast(data.error || "Delete failed", "error");
        return;
    }

    await loadFavorites();

    const modalElement = document.getElementById("allFavoritesModal");

    if (modalElement && modalElement.classList.contains("show")) {
        await refreshFavoritesModalContent();
    }

    showToast("Favorite deleted", "success");
}

function filterClosetModal() {
    const input = document.getElementById("closetSearchInput");
    if (!input) return;

    const query = input.value.toLowerCase();

    document.querySelectorAll("#closetModalBox .closet-card").forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(query) ? "" : "none";
    });
}

function filterFavoriteCards() {
    const input = document.getElementById("favoriteSearchInput");
    if (!input) return;

    const query = input.value.toLowerCase();

    document.querySelectorAll("#allFavoritesBox .all-favorite-card").forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(query) ? "" : "none";
    });
}

function filterFavoriteType(type) {
    document.querySelectorAll(".favorite-filter-row button").forEach(btn => {
        btn.classList.remove("active");
    });

    event.target.classList.add("active");

    if (type === "all") {
        document.querySelectorAll("#allFavoritesBox .all-favorite-card").forEach(card => {
            card.style.display = "";
        });
        return;
    }

    document.querySelectorAll("#allFavoritesBox .all-favorite-card").forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(type) ? "" : "none";
    });
}
