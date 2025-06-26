function getCVData() {
    let data = {
        name: $("h1[data-key='name']").text(),
        email: $("p[data-key='email']").text(),
        summary: $("p[data-key='summary']").text(),
        education: [],
        experience: []
    };

    $("#education .edu-item").each(function () {
        let inputs = $(this).find("input");
        data.education.push({
            institution: inputs.eq(0).val(),
            degree: inputs.eq(1).val(),
            year: inputs.eq(2).val()
        });
    });

    $("#experience .exp-item").each(function () {
        let inputs = $(this).find("input");
        data.experience.push({
            company: inputs.eq(0).val(),
            role: inputs.eq(1).val(),
            duration: inputs.eq(2).val()
        });
    });

    return data;
}

function saveCV() {
    $("#status").text("Saving...");
    $.ajax({
        url: "/save",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(getCVData()),
        success: function (res) {
            if (res.success) {
                $("#status").text("Saved successfully.");
            } else {
                $("#status").text("Error saving CV.");
            }
        }
    });
}

$(document).ready(function () {
    $("body").on("input", ".editable, input", function () {
        saveCV();
    });

    $("body").on("click", "#add-edu", function () {
        $("#education").append(`
            <div class="edu-item">
                <input type="text" class="edu" placeholder="Institution">
                <input type="text" class="edu" placeholder="Degree">
                <input type="text" class="edu" placeholder="Year">
                <button class="remove">Remove</button>
            </div>
        `);
    });

    $("body").on("click", "#add-exp", function () {
        $("#experience").append(`
            <div class="exp-item">
                <input type="text" class="exp" placeholder="Company">
                <input type="text" class="exp" placeholder="Role">
                <input type="text" class="exp" placeholder="Duration">
                <button class="remove">Remove</button>
            </div>
        `);
    });

    $("body").on("click", ".remove", function () {
        $(this).closest("div").remove();
        saveCV();
    });
});
