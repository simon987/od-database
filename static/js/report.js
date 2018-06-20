function drawSizeHistogram(rData) {

    let labels = [];
    let dataSet = [];

    for (let i in rData["sizes_histogram"]) {

        let slice = rData["sizes_histogram"][i];
        dataSet.push(slice[1]);
        labels.push("[" + humanFileSize(slice[0]) + ", " + humanFileSize(slice[0] + 10000000) + "]")
    }

    console.log(dataSet);

    let ctx = document.getElementById('sizeHistogram').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                data: dataSet,
                borderWidth: 1,
                borderColor: "#E94700",
                backgroundColor: "rgba(233, 71, 0, 0.6)"
            }],
            labels: labels,
            title: "test"

        },
        options: {
            title: {
                display: true,
                text: "Size histogram",
                fontColor: "#c6c6c6",
                fontSize: 16,
                fontFamily: "Lato,'Helvetica Neue',Arial,Helvetica,sans-serif"
            },
            legend: {
                display: false
            },
            scales: {
                yAxes: [
                    {
                        id: "count",
                        type: "logarithmic",
                        ticks: {
                            // Include a dollar sign in the ticks
                            callback: function (value, index, values) {

                                let log10 = Math.log10(value);

                                if (Number.isInteger(log10)) {
                                    return value;
                                }
                            }
                        }
                    }
                ]
            }
        }
    });
}

function drawDateHistogram(rData) {

    let labels = [];
    let dataSet = [];

    console.log(rData["dates_histogram"]);

    for (let i in rData["dates_histogram"]) {

        let slice = rData["dates_histogram"][i];
        dataSet.push(slice[1]);
        labels.push(slice[0])
    }

    let ctx = document.getElementById('dateHistogram').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                data: dataSet,
                borderWidth: 1,
                borderColor: "#E94700",
                backgroundColor: "rgba(233, 71, 0, 0.6)"
            }],
            labels: labels,

        },
        options: {
            title: {
                display: true,
                text: "Dates histogram",
                fontColor: "#c6c6c6",
                fontSize: 16,
                fontFamily: "Lato,'Helvetica Neue',Arial,Helvetica,sans-serif"
            },
            legend: {
                display: false
            },
            scales: {
                yAxes: [
                    {
                        id: "count",
                        type: "logarithmic",
                        ticks: {
                            // Include a dollar sign in the ticks
                            callback: function (value, index, values) {

                                let log10 = Math.log10(value);

                                if (Number.isInteger(log10)) {
                                    return value;
                                }
                            }
                        }
                    }
                ]
            }
        }
    });
}

function drawChart(rData) {

    var dataSetSize = [];
    var dataSetCount = [];
    var labels = [];
    var colors = [];

    var otherSize = 0;
    var otherCount = 0;

    for (var ext in rData["ext_stats"]) {

        dataSetSize.push(rData["ext_stats"][ext][0]);
        dataSetCount.push(rData["ext_stats"][ext][1]);
        labels.push(rData["ext_stats"][ext][2] + " x" + rData["ext_stats"][ext][1] + " (" + humanFileSize(rData["ext_stats"][ext][0]) + ")");
        colors.push(getRandomColor());
    }

    var ctx = document.getElementById('typesChart').getContext('2d');

    var fileTypePieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: dataSetSize,
                backgroundColor: colors,
                borderWidth: 1
            }, {
                data: dataSetCount,
                backgroundColor: colors,
                borderWidth: 1
            }],
            labels: labels

        },
        options: {
            title: {
                display: true,
                text: "File types for " + rData["base_url"] + " - " + humanFileSize(rData["total_size"]),
                fontColor: "#c6c6c6",
                fontSize: 16,
                fontFamily: "Lato,'Helvetica Neue',Arial,Helvetica,sans-serif"
            },
            legend: {
                labels: {
                    fontColor: "#bbbbbb",
                    fontFamily: "Lato,'Helvetica Neue',Arial,Helvetica,sans-serif",
                    boxWidth: 20,
                },
                position: "left"
            },
            cutoutPercentage: 15
        }
    });
}

function fillWebsiteTable(rData) {

    document.getElementById("baseUrl").innerHTML = rData["base_url"];
    document.getElementById("fileCount").innerHTML = rData["total_count"];
    document.getElementById("totalSize").innerHTML = humanFileSize(rData["total_size"]);
    document.getElementById("reportTime").innerHTML = rData["report_time"] + " UTC";

}

function fillDatabaseTable(rData) {
    document.getElementById("esIndexSize").innerHTML = humanFileSize(rData["es_index_size"]);
    document.getElementById("esSearchCount").innerHTML = rData["es_search_count"];
    document.getElementById("esSearchTime").innerHTML = rData["es_search_time"] + "ms";
    document.getElementById("esSearchTimeAvg").innerHTML = rData["es_search_time_avg"].toFixed(2) + "ms";
    document.getElementById("totalCount").innerHTML = rData["total_count"];
    document.getElementById("totalCountNonzero").innerText = rData["total_count_nonzero"];
    document.getElementById("totalSize").innerHTML = humanFileSize(rData["total_size"]);
    document.getElementById("sizeAvg").innerHTML = humanFileSize(rData["size_avg"]);
    document.getElementById("sizeStdDeviation").innerHTML = humanFileSize(rData["size_std_deviation"]);
    document.getElementById("sizeStdDeviationBounds").innerHTML = "[" + humanFileSize(rData["size_std_deviation_bounds"]["lower"]) +
        ", " + humanFileSize(rData["size_std_deviation_bounds"]["upper"]) + "]";
    document.getElementById("sizeVariance").innerHTML = humanFileSize(rData["size_variance"]);
}

function isRelevant(rData, ext, bySize) {

    if (ext[2] === "") {
        return false;
    }

    if (bySize) {
        return rData["ext_stats"][ext][1] > 0.03 * rData["total_count"]
    } else {
        return rData["ext_stats"][ext][0] > 0.002 * rData["total_size"]
    }


}

/**
 * https://stackoverflow.com/questions/1484506
 */
function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

/**
 * https://stackoverflow.com/questions/10420352
 */
function humanFileSize(bytes) {

    var thresh = 1000;
    if (Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    var units = ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while (Math.abs(bytes) >= thresh && u < units.length - 1);

    return bytes.toFixed(1) + ' ' + units[u];
}