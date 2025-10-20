---
title: "Economic & Market Dashboard"
description: "Real-time economic indicators and market data"
menu:
  main:
    weight: 2
---

<div id="dashboard-container">
  <div class="dashboard-updated" style="text-align: center; margin-bottom: 20px; color: #666;">
    Last updated: <span id="last-update">Loading...</span>
  </div>
  
  <div class="dashboard-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px;">
    
    <div class="metric-card" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
      <h4 style="margin: 0 0 10px 0; color: #333;">Consumer Confidence</h4>
      <div id="consumer-confidence">Loading...</div>
    </div>
    
    <div class="metric-card" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
      <h4 style="margin: 0 0 10px 0; color: #333;">S&P 500 (SPY)</h4>
      <div id="sp500">Loading...</div>
    </div>
    
    <div class="metric-card" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
      <h4 style="margin: 0 0 10px 0; color: #333;">CPI</h4>
      <div id="cpi">Loading...</div>
    </div>
    
    <div class="metric-card" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
      <h4 style="margin: 0 0 10px 0; color: #333;">Fed Funds Rate</h4>
      <div id="fed-rate">Loading...</div>
    </div>
    
    <div class="metric-card" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
      <h4 style="margin: 0 0 10px 0; color: #333;">Unemployment Rate</h4>
      <div id="unemployment">Loading...</div>
    </div>
    
    <div class="metric-card" style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
      <h4 style="margin: 0 0 10px 0; color: #333;">Employment (000s)</h4>
      <div id="employment">Loading...</div>
    </div>
    
  </div>
</div>

<script>
async function loadDashboard() {
  try {
    const response = await fetch("/data/dashboard.json");
    const data = await response.json();
    
    // Update timestamp
    document.getElementById("last-update").textContent = 
      new Date(data.updated).toLocaleString();
    
    // Consumer Confidence
    if(data.consumer_confidence && data.consumer_confidence.length > 0) {
      const cc = data.consumer_confidence[data.consumer_confidence.length - 1];
      document.getElementById("consumer-confidence").innerHTML = 
        `<div style="font-size: 1.8em; font-weight: bold; color: #2c3e50;">${cc.value.toFixed(1)}</div>
         <div style="color: #7f8c8d; font-size: 0.9em;">${cc.date}</div>`;
    }
    
    // S&P 500
    if(data.markets) {
      const sp = data.markets.find(m => m.symbol === "SPY");
      if (sp) {
        document.getElementById("sp500").innerHTML = 
          `<div style="font-size: 1.8em; font-weight: bold; color: #27ae60;">$${sp.close.toFixed(2)}</div>
           <div style="color: #7f8c8d; font-size: 0.9em;">${sp.date}</div>`;
      }
    }
    
    // CPI
    if(data.cpi) {
      document.getElementById("cpi").innerHTML = 
        `<div style="font-size: 1.8em; font-weight: bold; color: #e74c3c;">${data.cpi.value.toFixed(1)}</div>
         <div style="color: #7f8c8d; font-size: 0.9em;">${data.cpi.period}</div>`;
    }
    
    // Fed Rate
    if(data.fed_funds_rate) {
      document.getElementById("fed-rate").innerHTML = 
        `<div style="font-size: 1.8em; font-weight: bold; color: #3498db;">${data.fed_funds_rate.value}%</div>
         <div style="color: #7f8c8d; font-size: 0.9em;">${data.fed_funds_rate.date}</div>`;
    }
    
    // Unemployment
    if(data.unemployment) {
      document.getElementById("unemployment").innerHTML = 
        `<div style="font-size: 1.8em; font-weight: bold; color: #9b59b6;">${data.unemployment.value}%</div>
         <div style="color: #7f8c8d; font-size: 0.9em;">${data.unemployment.date}</div>`;
    }
    
    // Employment
    if(data.employment) {
      document.getElementById("employment").innerHTML = 
        `<div style="font-size: 1.8em; font-weight: bold; color: #34495e;">${data.employment.value.toLocaleString()}</div>
         <div style="color: #7f8c8d; font-size: 0.9em;">${data.employment.period}</div>`;
    }
    
  } catch (error) {
    console.error("Failed to load dashboard:", error);
    document.getElementById("last-update").textContent = "Error loading data";
  }
}

// Load on page load
loadDashboard();

// Refresh every 5 minutes
setInterval(loadDashboard, 300000);
</script>

