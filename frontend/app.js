var allData = [];

function populateYearDropdowns() {
    var fromSelect = document.getElementById("from-year");
    var toSelect = document.getElementById("to-year");
    var currentYear = new Date().getFullYear();
    
    for (var year = 2000; year <= currentYear; year++) {
        var option1 = document.createElement("option");
        option1.value = year;
        option1.text = year;
        if (year === 2019) option1.selected = true;
        fromSelect.appendChild(option1);
        
        var option2 = document.createElement("option");
        option2.value = year;
        option2.text = year;
        if (year === 2023) option2.selected = true;
        toSelect.appendChild(option2);
    }
}

function filterAndAggregateByYearRange(data, fromYear, toYear) {
    var filtered = data.filter(function(row) {
        return row.year >= fromYear && row.year <= toYear;
    });
    
    var areaData = {};
    for (var i = 0; i < filtered.length; i++) {
        var row = filtered[i];
        if (!areaData[row.area]) {
            areaData[row.area] = {
                area: row.area,
                parent: row.parent,
                publication_count: 0,
                faculty_count: 0
            };
        }
        areaData[row.area].publication_count += row.publication_count;
        areaData[row.area].faculty_count += row.faculty_count;
    }
    
    var mlArea = areaData["Machine learning"];
    if (!mlArea || mlArea.publication_count === 0) {
        return [];
    }
    
    var baseline = mlArea.faculty_count / mlArea.publication_count;
    
    var result = [];
    var areas = Object.keys(areaData).sort();
    for (var i = 0; i < areas.length; i++) {
        var area = areas[i];
        var data = areaData[area];
        
        if (data.publication_count === 0) {
            continue;
        }
        
        var facultyPerPub = data.faculty_count / data.publication_count;
        var iclrPoints = facultyPerPub / baseline;
        
        result.push({
            area: data.area,
            parent: data.parent,
            faculty_count: Math.round(data.faculty_count * 100) / 100,
            publication_count: data.publication_count,
            faculty_per_pub: Math.round(facultyPerPub * 100) / 100,
            iclr_points: Math.round(iclrPoints * 100) / 100
        });
    }
    
    return result;
}

function updateChart(fromYear, toYear) {
    var filteredData = filterAndAggregateByYearRange(allData, fromYear, toYear);
    
    var parentOrder= ["AI", "Systems", "Theory", "Interdisciplinary Areas"];
    filteredData.sort(function(a,b) {
        var pa = parentOrder.indexOf(a.parent || a.parent_area);
        var pb = parentOrder.indexOf(b.parent || b.parent_area);
        if(pa !== pb) return pa - pb;
        return a.area.localeCompare(b.area);
    });

    var areas = [];
    var values = [];
    var parents = [];
    for(var i = filteredData.length - 1; i >= 0; i--) {
        var row = filteredData[i];
        areas.push(row.area);
        values.push(row.iclr_points);
        parents.push(row.parent || row.parent_area);
    };
    
    var colorMap = {
        "AI": "#1f77b4",
        "Systems": "#ff7f0e",
        "Theory": "#2ca02c",
        "Interdisciplinary Areas": "#d62728"
    };
    var barColors = parents.map(function(p){
        return colorMap[p] || "#999";
    });

    var trace = {
        type: "bar",
        x: values,
        y: areas,
        orientation: "h",
        marker: {color: barColors},
        text: values.map(function(v) { return v.toFixed(2); }),
        textposition: 'outside'
    };

    var layout = {
        margin: { l: 230, r: 50, t: 20, b: 30 },
        xaxis: { title: "ICLR point" },
        yaxis: { automargin: true, title: "Area" },
        showlegend: false,
        height: 400 + filteredData.length * 10
    };

    if (document.getElementById("chart").data) {
        Plotly.react("chart", [trace], layout, { displaylogo: false });
    } else {
        Plotly.newPlot("chart", [trace], layout, { displaylogo: false });
    }
}

function getYearsFromInput() {
    var fromYear = parseInt(document.getElementById("from-year").value);
    var toYear = parseInt(document.getElementById("to-year").value);
    if (isNaN(fromYear)) fromYear = 2019;
    if (isNaN(toYear)) toYear = 2023;
    return { from: fromYear, to: toYear};
}

function setup(){
    populateYearDropdowns();

    fetch("http://localhost:8001/iclr_points_all")
        .then(function(response){
            return response.json();
        })
        .then(function(data){
            allData = data;
            var yrs = getYearsFromInput();
            updateChart(yrs.from, yrs.to);
        })
        .catch(function(error) {
            console.error("Error loading data:", error);
        });

    var btn = document.getElementById("update-range");
    btn.addEventListener("click", function(){
        var yrs = getYearsFromInput();
        updateChart(yrs.from, yrs.to);
    });
}

setup();

