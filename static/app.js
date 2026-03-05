const priceEl = document.getElementById("price");
const updatedEl = document.getElementById("updated");

async function loadPrice() {
  try {
    const response = await fetch("/api/bitcoin-price");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unknown backend error");
    }

    priceEl.textContent = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: data.currency,
      maximumFractionDigits: 2,
    }).format(data.price);

    const updatedTime = new Date(data.timestamp).toLocaleString();
    updatedEl.textContent = `Last updated: ${updatedTime}`;
  } catch (error) {
    console.error("Failed to load BTC price:", error);
    priceEl.textContent = "Unavailable";
    updatedEl.textContent = `Last updated: error (${error.message})`;
  }
}

loadPrice();
setInterval(loadPrice, 30000);
