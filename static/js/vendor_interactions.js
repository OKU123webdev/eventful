// VENDOR INTERACTIONS (MARK INTERESTED, FAVOURITE, AI INSIGHTS)

// MARK AS INTRTESTED / UNMARK AS INTRESTED
$(document).ready(function() {
    // toggle mark intrested button
    $(document).on("click", ".toggle-interest", function() {
        const button = $(this);
        const vendorId = button.data("vendor-id");
        const isAdding = !button.hasClass("btn-success");
        
        // find card with selected vendor name
        const card = button.closest(".card");
        const vendorName = card.find(".card-title").text() || button.data("vendor-name");

        // call route based on action
        const targetUrl = isAdding ? "/mark-interested" : "/remove-vendor";

        $.ajax({
            url: targetUrl,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ 
                place_id: vendorId,
                vendor_name: vendorName,
                vendor_type: new URLSearchParams(window.location.search).get('vendor_type')
            }),
            success: function(response) {
                if (response.success) {
                    // ADD VENDOR TO TABLE
                    if (isAdding) {
                        // switch Button to Green
                        button.removeClass("btn_intrest").addClass("btn-success")
                              .html('<i class="bi bi-check-circle me-2"></i>Added');

                        // show table and add row
                        $("#no-vendors-msg").hide();
                        $("#vendor-table-container").show();
                        
                        const newRow = `
                            <tr data-vendor-id="${vendorId}">
                                <td class="align-middle text-center"><i class="bi bi-star"></i></td>
                                <td class="align-middle"><div class="fw-bold text-dark">${vendorName}</div></td>
                                <td class="align-middle fw-bold">-</td>
                                <td class="align-middle fst-italic">Interested</td>
                                <td class="align-middle text-center">
                                    <div class="d-flex justify-content-center gap-2">
                                        <button class="btn btn-action view">View</button>
                                        <button class="btn btn-outline-danger btn-sm remove">Remove</button>
                                    </div>
                                </td>
                            </tr>`;
                        $(newRow).hide().appendTo("#selected-vendors-tbody").fadeIn(500);
                    // REMOVE VENDOR FROM TABLE
                    } else {
                        // Switch button back to Blue
                        button.removeClass("btn-success").addClass("btn_intrest")
                              .html('<i class="bi bi-plus-circle me-2"></i>Mark Interested');

                        // Remove from table
                        removeRowFromTable(vendorId);
                    }
                }
            }
        });
    });

    // My Vendors table - 'Remove' button 
    $(document).on("click", ".remove", function() {
        const row = $(this).closest("tr");
        const vendorId = row.data("vendor-id");

        $.ajax({
            url: "/remove-vendor",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ place_id: vendorId }),
            success: function(response) {
                if (response.success) {
                    // remove row fromt table
                    removeRowFromTable(vendorId);
                    
                    // find vendor in Google results and reset button
                    const resultBtn = $(`.toggle-interest[data-vendor-id="${vendorId}"]`);
                    if (resultBtn.length) {
                        resultBtn.removeClass("btn-success").addClass("btn_intrest")
                                 .html('<i class="bi bi-plus-circle me-2"></i>Mark Interested');
                    }
                }
            }
        });
    });

    // Remove row from table
    function removeRowFromTable(vendorId) {
        $(`tr[data-vendor-id="${vendorId}"]`).fadeOut(300, function() {
            $(this).remove();
            if ($("#selected-vendors-tbody tr").length === 0) {
                $("#vendor-table-container").hide();
                $("#no-vendors-msg").show();
            }
        });
    }
});

// toggle favourite star/db
$(document).ready(function() {
    $(document).on("click", ".star-icon", function() {
        const star = $(this);
        const placeId = star.data("id");

        $.post(`/toggle-favourite/${placeId}`, function(data) {
            if (data.success) {
                star.toggleClass("bi-star-fill", data.is_favourite);
                star.toggleClass("bi-star", !data.is_favourite);
            }
        });
    });
});

// BUDGET ANALYSIS / AI INSIGHTS
document.addEventListener("DOMContentLoaded", () => {
  const aiBtn = document.getElementById("aiBtn");
  const aiCard = document.getElementById("aiCard");
  const aiResults = document.getElementById("aiResults");
  const aiSummary = document.getElementById("aiSummary");

  // error handling
  if (!aiBtn || !aiCard || !aiResults) return;

  // get vendor_type from URL
  function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
  }

  // prevent HTML injecetion
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // loading icon
  function setLoadingState(isLoading) {
    aiBtn.disabled = isLoading;

    if (isLoading) {
      aiBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Generating...`;
    } else {
      aiBtn.innerHTML = `<i class="bi bi-magic me-2"></i>Get AI recommendation`;
    }
  }

  // error message
  function renderError(message) {
    aiResults.innerHTML = `
      <div class="vendorDirectory_aiPick">
        <div class="vendorDirectory_aiPickName">Couldn’t generate AI recommendation</div>
        <div class="vendorDirectory_aiLine">${escapeHtml(message)}</div>
      </div>
    `;
    if (aiSummary) aiSummary.style.display = "none";
    aiCard.style.display = "block";
  }

  // RENDER AI RECOMMENDATIONS
  function renderAI(data) {

    const ranking = Array.isArray(data.ranking) ? data.ranking : [];

    // no results
    if (ranking.length === 0) {
      renderError("AI returned no ranking results.");
      return;
    }

    // show HTML 
    aiResults.innerHTML = ranking.slice(0, 3).map((item, idx) => {
      const rating = item.google_rating ?? "—";
      return `
        <div class="vendorDirectory_aiPick" data-place-id="${escapeHtml(item.place_id)}">
          <div class="vendorDirectory_aiPickTop">
            <div class="vendorDirectory_aiPickName">${idx + 1}. ${escapeHtml(item.name || "")}</div>
            <div class="vendorDirectory_aiScore">${escapeHtml(rating)}/5</div>
          </div>

          <div class="vendorDirectory_aiLine">
            <span class="vendorDirectory_aiLabel">Why:</span> ${escapeHtml(item.why)}
          </div>

          <div class="vendorDirectory_aiLine">
            <span class="vendorDirectory_aiLabel">Risks:</span> ${escapeHtml(item.risks)}
          </div>
        </div>
      `;
    }).join("");

    // AI summary
    if (aiSummary) {
      if (data.notes && String(data.notes).trim().length > 0) {
        aiSummary.style.display = "block";
        aiSummary.textContent = data.notes;
      } else {
        aiSummary.style.display = "none";
      }
    }

    aiCard.style.display = "block";

    // highlight top pick
    if (data.best_place_id) {
      highlightBestVendor(data.best_place_id);
    }
  }

  // HIGHLIGHT TOP PICK
  function highlightBestVendor(bestPlaceId) {
    const selector = `[data-vendor-id="${CSS.escape(bestPlaceId)}"]`;
    const vendorCard = document.querySelector(selector);

    if (!vendorCard) return;

    vendorCard.style.outline = "3px solid var(--gold)";
    vendorCard.style.outlineOffset = "4px";
  }

  // CALL AI ENDPOINT
  async function fetchAiRanking() {
    const vendorType = getQueryParam("vendor_type");
    const pageToken = getQueryParam("page_token");

    // check vendor_type exsists
    if (!vendorType) {
      renderError("Missing vendor_type in URL.");
      return;
    }

    // build query string for AI route
    const qs = new URLSearchParams();
    qs.set("vendor_type", vendorType);
    if (pageToken) qs.set("page_token", pageToken);

    const url = `/vendor-directory/ai-rank?${qs.toString()}`;

    // turn on loading state
    setLoadingState(true);

    try {
      const res = await fetch(url, { method: "GET" });
      const data = await res.json(); // parse JSON response

      // if HTTP response not OK
      if (!res.ok) {
        const msg = data?.detail || data?.error || "Unknown error.";
        renderError(msg);
        return;
      }

      const withNames = addNamesFromDom(data);
      renderAI(withNames);

    } catch (err) {
      renderError(err?.message || "Request failed.");
    } finally {
      setLoadingState(false);
    }
  }

  // MATCH VENDOR RESULTS TO AI RANKING
  function addNamesFromDom(data) {
    if (!data || !Array.isArray(data.ranking)) return data; // return unchanged if missing

    // add to ranking
    const newRanking = data.ranking.map(item => {
      const placeId = item.place_id;
      if (!placeId) return item;

      const card = document.querySelector(`[data-vendor-id="${placeId}"]`);
      if (!card) return item;

      const title = card.querySelector(".card-title");
      const name = title ? title.textContent.trim() : "";

      return { ...item, name };
    });

    return { ...data, ranking: newRanking };
  }

  // Click handler
  aiBtn.addEventListener("click", (e) => {
    e.preventDefault();

    // Clear old results before generating new
    aiResults.innerHTML = "";
    if (aiSummary) aiSummary.style.display = "none";

    fetchAiRanking();
  });
});