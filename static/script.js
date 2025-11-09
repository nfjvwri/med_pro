// small client-side JS for instant calc and saving
document.addEventListener("DOMContentLoaded", () => {
  // For index page quick calc
  const weight = document.getElementById("weight");
  const height = document.getElementById("height");
  const calcBtn = document.getElementById("calcBtn");
  const saveBtn = document.getElementById("saveBtn");
  const bmiScore = document.getElementById("bmiScore");
  const bmiCategory = document.getElementById("bmiCategory");
  const advice = document.getElementById("advice");

  // Dashboard elements (if present)
  const s_weight = document.getElementById("s_weight");
  const s_height = document.getElementById("s_height");
  const s_note = document.getElementById("s_note");
  const s_calc = document.getElementById("s_calc");
  const s_bmi = document.getElementById("s_bmi");
  const s_cat = document.getElementById("s_cat");
  const s_cancel = document.getElementById("s_cancel");

  // read login state set server-side
  const loggedIn = window.APP && window.APP.loggedIn;

  if (saveBtn) {
    saveBtn.disabled = !loggedIn;
    saveBtn.title = loggedIn ? "" : "Login to save results";
  }

  function classify(bmi) {
    if (bmi < 18.5) return "Underweight";
    if (bmi < 25) return "Healthy";
    if (bmi < 30) return "Overweight";
    return "Obese";
  }

  function adviceText(cat) {
    switch (cat) {
      case "Underweight": return "BMI below healthy range — consider a nutrient-dense diet and consult a professional if needed.";
      case "Healthy": return "Within healthy range — keep doing balanced diet & exercise.";
      case "Overweight": return "Slightly above healthy range — consider lifestyle adjustments.";
      case "Obese": return "BMI indicates obesity. Consider seeking professional guidance.";
    }
  }

  function computeAndShow(wVal, hVal, targetElements){
    const w = parseFloat(wVal);
    const hcm = parseFloat(hVal);
    if (!isFinite(w) || !isFinite(hcm) || w <= 0 || hcm <= 0) {
      targetElements.bmi.textContent = "—";
      targetElements.cat.textContent = "Enter valid values";
      targetElements.advice && (targetElements.advice.textContent = "");
      return null;
    }
    const h = hcm / 100.0;
    const bmi = Math.round((w / (h * h)) * 10) / 10;
    const cat = classify(bmi);
    targetElements.bmi.textContent = bmi;
    targetElements.cat.textContent = cat;
    targetElements.advice && (targetElements.advice.textContent = adviceText(cat));
    return { b: bmi, c: cat };
  }

  if (calcBtn) {
    calcBtn.addEventListener("click", () => {
      computeAndShow(
        weight.value,
        height.value,
        { bmi: bmiScore, cat: bmiCategory, advice: advice }
      );
    });
  }

  // Save button: if user logged in, send to server (index page)
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      if (!loggedIn) {
        alert("Please login to save measurements.");
        return;
      }
      const result = computeAndShow(weight.value, height.value, { bmi: bmiScore, cat: bmiCategory, advice: advice });
      if (!result) return;
      // call server-side API to save
      try {
        const resp = await fetch("/api/save_bmi", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            weight: parseFloat(weight.value),
            height_cm: parseFloat(height.value),
            bmi: result.b,
            category: result.c,
            note: "Saved from quick form"
          })
        });
        const data = await resp.json();
        if (data.ok) {
          alert("Saved to your history.");
        } else {
          alert("Save failed: " + (data.error || "unknown"));
        }
      } catch (err) {
        alert("Network error saving BMI.");
      }
    });
  }

  // dashboard save form
  if (s_calc) {
    s_calc.addEventListener("click", async () => {
      const res = computeAndShow(
        s_weight.value,
        s_height.value,
        { bmi: s_bmi, cat: s_cat, advice: null }
      );
      if (!res) return;
      // send to server
      try {
        const resp = await fetch("/api/save_bmi", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            weight: parseFloat(s_weight.value),
            height_cm: parseFloat(s_height.value),
            bmi: res.b,
            category: res.c,
            note: s_note.value || null
          })
        });
        const data = await resp.json();
        if (data.ok) {
          alert("Saved — refresh to see in history.");
          // optional quick reset
          s_weight.value = "";
          s_height.value = "";
          s_note.value = "";
          s_bmi.textContent = "—";
          s_cat.textContent = "—";
        } else {
          alert("Save failed: " + (data.error || "unknown"));
        }
      } catch (err) {
        alert("Network error saving BMI.");
      }
    });
    s_cancel.addEventListener("click", () => {
      s_weight.value = "";
      s_height.value = "";
      s_note.value = "";
      s_bmi.textContent = "—";
      s_cat.textContent = "—";
    });
  }

});
