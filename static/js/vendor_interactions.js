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
                        // Switch Button to Green
                        button.removeClass("btn_intrest").addClass("btn-success")
                              .html('<i class="bi bi-check-circle me-2"></i>Added');

                        // Show table and add row
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
                    // Remove row fromt table
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

// toggle favourite
$(document).ready(function() {
    $('.star-icon').click(function() {
        const star = $(this);
        const vendorId = star.data('id');

        $.post(`/toggle-favourite/${vendorId}`, function(data) {
            if (data.success) {
                star.toggleClass('fill-star', data.is_favorite);
            } else {
                console.error('Error toggling favourite:', data.error);
            }
        });
    });

});