

function drawChart(rData) {

    var dataSetSize = [];
    var dataSetCount = [];
    var labels = [];
    var colors = [];

    var otherSize = 0;
    var otherCount = 0;

    for(var ext in rData["ext_stats"]) {
        //Ignore file sizes below 0.5%
        if (!isRelevant(rData, ext)) {

            otherSize += rData["ext_stats"][ext][0];
            otherCount += rData["ext_stats"][ext][1];

        } else {
            dataSetSize.push(rData["ext_stats"][ext][0]);
            dataSetCount.push(rData["ext_stats"][ext][1]);
            labels.push(rData["ext_stats"][ext][2] + " x" + rData["ext_stats"][ext][1] + " (" + humanFileSize(rData["ext_stats"][ext][0]) + ")");
            colors.push(getRandomColor())
        }
    }

    if(otherCount !== 0) {
        colors.push(getRandomColor());
        labels.push("other x" + otherCount + " (" + humanFileSize(otherSize) + ")");
        dataSetSize.push(otherSize);
        dataSetCount.push(otherCount);
    }

    var ctx = document.getElementById('typesChart').getContext('2d');

    var fileTypePieChart = new Chart(ctx,{
        type: 'pie',
        data: {
            datasets: [{
                data: rData["total_size"] < 100000 ? dataSetCount : dataSetSize,
                backgroundColor: colors
            }],

            labels: labels

        },
        options: {
            title: {
                display: true,
                text: "File types for " + rData["base_url"] + " - " + humanFileSize(rData["total_size"])
            }
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
    document.getElementById("esIndexSize") .innerHTML = humanFileSize(rData["es_index_size"]);
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

function isRelevant(rData, ext) {

    // if (ext[2] === "") {
    //     return false;
    // }

    if(rData["total_size"] < 100000) {
        return rData["ext_stats"][ext][1] > 0.03 * rData["total_count"]
    } else {
        return rData["ext_stats"][ext][0] > 0.005 * rData["total_size"]
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

    if(bytes === 0) {
        return "? B"
    }

    var thresh = 1000;
    if(Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    var units = ['kB','MB','GB','TB','PB','EB','ZB','YB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while(Math.abs(bytes) >= thresh && u < units.length - 1);

    return bytes.toFixed(1) + ' ' + units[u];
}