document.addEventListener("DOMContentLoaded", function () {

    const graficoProduccion = document.getElementById("produccionDia");

    if (graficoProduccion) {
        new Chart(graficoProduccion, {
            type: "line",
            data: {
                labels: window.labels_dias,
                datasets: [{
                    label: "Raciones entregadas",
                    data: window.data_dias,
                    tension: 0.35
                }]
            },
            options: {
                responsive: true
            }
        });
    }

    const graficoProducto = document.getElementById("productoChart");

    if (graficoProducto) {
        new Chart(graficoProducto, {
            type: "doughnut",
            data: {
                labels: window.labels_productos,
                datasets: [{
                    data: window.data_productos
                }]
            }
        });
    }

});