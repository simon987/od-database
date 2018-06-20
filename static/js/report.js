function drawSizeHistogram(rData) {

    let labels = [];
    let dataSet = [];

    for (let i in rData["sizes_histogram"]) {

        let slice = rData["sizes_histogram"][i];
        dataSet.push(slice[1]);
        labels.push("[" + humanFileSize(slice[0]) + ", " + humanFileSize(slice[0] + 10000000) + "]")
    }

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

    let dataSetSize = [];
    let dataSetCount = [];
    let labels = [];
    let colors = [];

    for (let ext in rData["ext_stats"]) {

        dataSetSize.push(rData["ext_stats"][ext][0]);
        dataSetCount.push(rData["ext_stats"][ext][1]);
        labels.push(rData["ext_stats"][ext][2] + " x" + rData["ext_stats"][ext][1] + " (" + humanFileSize(rData["ext_stats"][ext][0]) + ")");

        let category = category_map.hasOwnProperty(rData["ext_stats"][ext][2]) ? category_map[rData["ext_stats"][ext][2]] : "default";
        colors.push(getRandomTintOfColor(colors_map[category]));
    }

    let ctx = document.getElementById('typesChart').getContext('2d');

    let fileTypePieChart = new Chart(ctx, {
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

function getRandomTintOfColor(color) {
    let p = 1,
        temp,
        random = Math.random(),
        result = '#';

    while (p < color.length) {
        temp = parseInt(color.slice(p, p += 2), 16);
        temp += Math.floor((16 - temp) * random);
        result += temp.toString(16).padStart(2, '0');
    }
    return color;
}

category_map = {

    //Application category
    'bcpio': 'application', 'bin': 'application',
    'cdf': 'application', 'csh': 'application',
    'dll': 'application', 'doc': 'application',
    'dot': 'application', 'dvi': 'application',
    'eml': 'application', 'exe': 'application',
    'hdf': 'application', 'man': 'application',
    'me': 'application', 'mht': 'application',
    'mhtml': 'application', 'mif': 'application',
    'ms': 'application', 'nc': 'application',
    'nws': 'application', 'o': 'application',
    'obj': 'application', 'oda': 'application',
    'p12': 'application', 'p7c': 'application',
    'pfx': 'application', 'tr': 'application',
    'ppa': 'application', 'pps': 'application',
    'ppt': 'application', 'ps': 'application',
    'pwz': 'application', 'pyc': 'application',
    'pyo': 'application', 'ram': 'application',
    'rdf': 'application', 'roff': 'application',
    'sh': 'application', 'so': 'application',
    'src': 'application', 'sv4cpio': 'application',
    'sv4crc': 'application', 't': 'application',
    'tcl': 'application', 'tex': 'application',
    'texi': 'application', 'texinfo': 'application',
    'ustar': 'application', 'wiz': 'application',
    'wsdl': 'application', 'xlb': 'application',
    'xls': 'application', 'xpdl': 'application',
    'xsl': 'application', 'torrent': 'application',
    //Text category
    'java': 'text', 'cpp': 'text', 'rb': 'text',
    'bat': 'text', 'latex': 'text', 'xml': 'text',
    'etx': 'text', 'htm': 'text', 'c': 'text',
    'css': 'text', 'csv': 'text', 'html': 'text',
    'js': 'text', 'json': 'text', 'ksh': 'text',
    'pl': 'text', 'pot': 'application', 'py': 'text',
    'h': 'text', 'tsv': 'text', 'rtx': 'text',
    'sgm': 'text', 'sgml': 'text', 'txt': 'text',
    'vcf': 'text', 'pdf': 'text', 'epub': 'text',
    'srt': 'text',
    //Video category
    '3g2': 'video', '3gp': 'video', 'asf': 'video',
    'asx': 'video', 'avi': 'video', 'flv': 'video',
    'swf': 'video', 'vob:': 'video', 'qt': 'video',
    'webm': 'video', 'mov': 'video', 'm1v': 'video',
    'm3u': 'video', 'm3u8': 'video', 'movie': 'video',
    'mp4': 'video', 'mpa': 'video', 'mpe': 'video',
    'mpeg': 'video', 'mpg': 'video', 'mkv': 'video',
    'wmv': 'video',
    // Audio category
    'wav': 'audio', 'snd': 'audio', 'mp2': 'audio',
    'aif': 'audio', 'iff': 'audio', 'm4a': 'audio',
    'mid': 'audio', 'midi': 'audio', 'mp3': 'audio',
    'wma': 'audio', 'ra': 'audio', 'aifc': 'audio',
    'aiff': 'audio', 'au': 'audio', 'flac': 'audio',
    // Image category
    'bmp': 'image', 'gif': 'image', 'jpg': 'image',
    'xwd': 'image', 'tif': 'image', 'tiff': 'image',
    'png': 'image', 'pnm': 'image', 'ras': 'image',
    'ico': 'image', 'ief': 'image', 'pgm': 'image',
    'jpe': 'image', 'pbm': 'image', 'jpeg': 'image',
    'ppm': 'image', 'xpm': 'image', 'xbm': 'image',
    'rgb': 'image', 'svg': 'image', 'psd': 'image',
    'yuv': 'image', 'ai': 'image', 'eps': 'image',
    // Archive category
    'ar': 'archive', 'cpio': 'archive', 'shar': 'archive',
    'iso': 'archive', 'lbr': 'archive', 'mar': 'archive',
    'sbx': 'archive', 'bz2': 'archive', 'f': 'archive',
    'gz': 'archive', 'lz': 'archive', 'lzma': 'archive',
    'lzo': 'archive', 'rz': 'archive', 'sfark': 'archive',
    'sz': 'archive', 'z': 'archive', '7z': 'archive',
    's7z': 'archive', 'ace': 'archive', 'afa': 'archive',
    'alz': 'archive', 'apk': 'archive', 'arc': 'archive',
    'arj': 'archive', 'b1': 'archive', 'b6z': 'archive',
    'a': 'archive', 'bh': 'archive', 'cab': 'archive',
    'car': 'archive', 'cfs': 'archive', 'cpt': 'archive',
    'dar': 'archive', 'dd': 'archive', 'dgc': 'archive',
    'dmg': 'archive', 'ear': 'archive', 'gca': 'archive',
    'ha': 'archive', 'hki': 'archive', 'ice': 'archive',
    'jar': 'archive', 'kgb': 'archive', 'lzh': 'archive',
    'lha': 'archive', 'lzx': 'archive', 'pak': 'archive',
    'partimg': 'archive', 'paq6': 'archive', 'paq7': 'archive',
    'paq8': 'archive', 'pea': 'archive', 'pim': 'archive',
    'pit': 'archive', 'qda': 'archive', 'rar': 'archive',
    'rk': 'archive', 'sda': 'archive', 'sea': 'archive',
    'sen': 'archive', 'sfx': 'archive', 'shk': 'archive',
    'sit': 'archive', 'sitx': 'archive', 'sqx': 'archive',
    'tbz2': 'archive', 'tlz': 'archive', 'xz': 'archive',
    'txz': 'archive', 'uc': 'archive', 'uc0': 'archive',
    'uc2': 'archive', 'ucn': 'archive', 'ur2': 'archive',
    'ue2': 'archive', 'uca': 'archive', 'uha': 'archive',
    'war': 'archive', 'wim': 'archive', 'xar': 'archive',
    'xp3': 'archive', 'yz1': 'archive', 'zip': 'archive',
    'zipx': 'archive', 'zoo': 'archive', 'zpaq': 'archive',
    'zz': 'archive', 'xpi': 'archive', 'tgz': 'archive',
    'tbz': 'archive'
};

colors_map = {
    "archive": "#23d630",
    "application": "#8fb847",
    "image": "#c55fce",
    "audio": "#00a4e2",
    "video": "#dc7846",
    "text": "#e1ba45",
    "default": "#CCCCCC"
};

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