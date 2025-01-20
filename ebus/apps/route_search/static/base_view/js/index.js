document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("search-btn").addEventListener("click", function () {
        const startLocation = document.getElementById('firstStation').value;
        const goalLocation = document.getElementById('goalStation').value;
        const datetime = document.getElementById('datetime').value;

        // Check if all required fields are filled
        if (startLocation && goalLocation && datetime) {
          document.getElementById("routeForm").style.display = "none";
          let loader = document.getElementById("loader")
          loader.classList.add("show");
          document.getElementById("foundRoutes").style.display = "block";
        }
    });
});

function backFunctionRoutes() {
    current_solution = null;
    document.getElementById("routeForm").style.display = "block";
    const container = document.getElementById("foundRoutes");
    container.innerHTML = '<span id="loader"</span>';
    container.style.display = "none";
    document.getElementById("departureDetails").style.display = "none";
    const elementsToDelete = container.querySelectorAll('.route');
    elementsToDelete.forEach((element) => {
        element.remove();
    });
    const elementsToDelete2 = container.querySelectorAll('.roadType');
    elementsToDelete2.forEach((element) => {
        element.remove();
    });
    removeRoutingControl()
    document.getElementById("back-btn").style.display = "none";
    document
        .getElementById("back-btn")
        .removeEventListener("click", backFunctionRoutes);
}


