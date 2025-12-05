document.addEventListener('DOMContentLoaded', function () {
    const API_URL = '/api/financial-ratios/';

    let globalData = null;

    // --- 1. FETCH DATA ---
    fetch(API_URL)
        .then(response => response.json())
        .then(data => {
            globalData = data;
            initDashboard(data);
        })
        .catch(error => console.error('Error fetching data:', error));

    // --- 2. INITIALIZE ---
    function initDashboard(data) {
        const stockSelect = document.getElementById('stock-select');
        const stockCodes = Object.keys(data);

        // Populate Dropdown
        stockCodes.forEach(code => {
            const option = document.createElement('option');
            option.value = code;
            option.text = code;
            stockSelect.appendChild(option);
        });

        // Mặc định chọn mã đầu tiên
        if (stockCodes.length > 0) {
            updateCharts(stockCodes[0]);
        }

        // Sự kiện đổi mã cổ phiếu
        stockSelect.addEventListener('change', function () {
            updateCharts(this.value);
        });
    }

    // --- 3. UPDATE CHARTS (LOGIC CHÍNH ĐÃ SỬA ĐỔI) ---
    function updateCharts(stockCode) {
        const companyData = globalData[stockCode];
        if (!companyData || !companyData.annual_reports) return;

        // --- CẬP NHẬT HEADER (Thêm đoạn này) ---
        // Lấy số năm từ dữ liệu JSON
        const totalYears = companyData.TongSoNamThuThap || 0; 
        // Cập nhật vào thẻ HTML
        const yearSpan = document.getElementById('total-year-collected');
        if (yearSpan) {
            yearSpan.innerText = totalYears;
        }
        // ---------------------------------------
        
        // Chuyển đổi dữ liệu sang mảng và sắp xếp theo năm
        const chartData = Object.entries(companyData.annual_reports)
            .map(([year, metrics]) => ({
                year: year,
                ...metrics
            }))
            .sort((a, b) => a.year - b.year);

        // A. Cập nhật KPI Cards (PE, PB, Tỷ lệ Nợ dài hạn)
        updateKPIs(chartData);

        // B. Vẽ các biểu đồ chi tiết
        // 1. Biểu đồ PE (Số lần - không phải %)
        drawSingleLineChart('#chart-pe', chartData, 'PE', '#0d47a1', false); 
        
        // 2. Biểu đồ PB (Số lần - không phải %)
        drawSingleLineChart('#chart-pb', chartData, 'PB', '#42a5f5', false);

        // 3. Biểu đồ EPS (Số tuyệt đối - Dùng Bar Chart cho đẹp)
        drawSimpleBarChart('#chart-eps', chartData, 'EPS', '#66bb6a');

        // 4. Biểu đồ Tỷ lệ Nợ dài hạn (% - Có flag isPercent = true)
        drawSingleLineChart('#chart-tyle-no-dai-han', chartData, 'TyLeNoDaiHan', '#ef5350', true);
    }

    // --- 4. UPDATE KPI CARDS ---
    function updateKPIs(data) {
        // Vẽ KPI PE (Không phải %)
        drawKpiChart('#kpi-pe', data, 'PE', false);
        
        // Vẽ KPI PB (Không phải %)
        drawKpiChart('#kpi-pb', data, 'PB', false);
        
        // Vẽ KPI Tỷ lệ Nợ Dài Hạn (Là %)
        drawKpiChart('#kpi-tyle-no-dai-han', data, 'TyLeNoDaiHan', true);
    }

    // ============================================================
    // D3.JS CHART FUNCTIONS
    // ============================================================

    function setupCanvas(selector) {
        d3.select(selector).selectAll("*").remove();
        const container = document.querySelector(selector);
        // Fallback nếu container chưa render
        const width = container ? container.clientWidth : 300;
        const height = container ? (container.clientHeight - 10) : 200;
        const margin = { top: 20, right: 30, bottom: 30, left: 50 }; // Tăng left margin để chứa số lớn (EPS)

        const svg = d3.select(selector)
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        return { svg, width: width - margin.left - margin.right, height: height - margin.top - margin.bottom };
    }

    // --- KPI CHART (Dạng cột đơn năm cuối) ---
    function drawKpiChart(selector, data, key, isPercent) {
        const container = d3.select(selector);
        container.html(""); 

        const width = document.querySelector(selector).clientWidth;
        const height = document.querySelector(selector).clientHeight;
        const paddingBottom = 20; 
        const chartHeight = height - paddingBottom;

        const svg = container.append("svg")
            .attr("width", width)
            .attr("height", height);

        // Lấy dữ liệu năm cuối
        const latestItem = data[data.length - 1];
        // Nếu giá trị null thì coi là 0
        const latestValue = (latestItem && latestItem[key] !== null) ? latestItem[key] : 0;

        // Xử lý dữ liệu sạch để tính scale
        const validData = data.map(d => ({
            year: d.year,
            value: d[key] === null ? 0 : d[key]
        }));
        
        // Chỉ lấy năm cuối để vẽ
        const finalYearData = validData.length > 0 ? [validData[validData.length - 1]] : [];

        // Scales
        const x = d3.scaleBand()
            .domain(finalYearData.map(d => d.year))
            .range([0, width])
            .padding(0.3);

        const yMax = d3.max(validData, d => d.value) || 1; 
        const y = d3.scaleLinear()
            .domain([0, yMax * 1.2]) 
            .range([chartHeight, 0]);

        // Trục X (Ẩn đường kẻ)
        const xAxis = svg.append("g")
            .attr("transform", `translate(0, ${chartHeight})`)
            .call(d3.axisBottom(x).tickSize(0));
        xAxis.select(".domain").remove();
        xAxis.selectAll("text").style("fill", "#666").attr("dy", "10");

        // Vẽ cột
        svg.selectAll(".bar")
            .data(finalYearData)
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", d => x(d.year))
            .attr("width", x.bandwidth())
            .attr("y", d => y(d.value))
            .attr("height", d => chartHeight - y(d.value))
            .attr("fill", "#0f2b4a")
            .attr("rx", 4);

        // Hiển thị số liệu (Big Number)
        let formattedValue = latestValue.toFixed(2);
        if (isPercent) {
            formattedValue = (latestValue * 100).toFixed(2) + '%';
        } else {
            // Nếu số quá lớn (ví dụ EPS > 1000), format có dấu phẩy
            if (latestValue > 1000) formattedValue = d3.format(",.0f")(latestValue);
        }

        svg.append("text")
            .attr("x", width / 2)
            .attr("y", chartHeight / 2)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .style("font-size", "20px")
            .style("font-weight", "bold")
            .style("fill", "#333")
            .style(
            "text-shadow",
            "0px 0px 4px rgba(255,255,255,0.9), \
            2px 2px 4px rgba(255,255,255,0.9), \
            -2px -2px 4px rgba(255,255,255,0.9), \
            2px -2px 4px rgba(255,255,255,0.9), \
            -2px 2px 4px rgba(255,255,255,0.9)"
            )
            .text(formattedValue);
    }

    // --- SINGLE LINE CHART (Dùng cho PE, PB, Tỷ lệ Nợ) ---
    // isPercent = true: Nhân 100 và thêm %, false: Giữ nguyên
    function drawSingleLineChart(selector, data, key, color, isPercent = false) {
        const { svg, width, height } = setupCanvas(selector);
        
        const validData = data.filter(d => d[key] !== null);

        // Trục X
        const x = d3.scalePoint().domain(data.map(d => d.year)).range([0, width]).padding(0.5);
        svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));

        // Trục Y
        // Nếu là %, domain tính theo giá trị * 100
        // Nếu là số thường, domain giữ nguyên
        const yValue = d => isPercent ? d[key] * 100 : d[key];
        
        const yMax = d3.max(validData, d => yValue(d));
        const y = d3.scaleLinear()
            .domain([0, (yMax || 1) * 1.2]) // *1.2 để chừa khoảng trống trên đầu
            .range([height, 0]);

        // Vẽ trục Y
        svg.append("g").call(d3.axisLeft(y).ticks(5));

        // Line Generator
        const line = d3.line()
            .x(d => x(d.year))
            .y(d => y(yValue(d)));

        // Vẽ đường
        svg.append("path")
            .datum(validData)
            .attr("fill", "none")
            .attr("stroke", "#b0bec5")
            .attr("stroke-width", 1)
            .attr("d", line);

        // Vẽ chấm tròn
        svg.selectAll("circle")
            .data(validData)
            .enter().append("circle")
            .attr("cx", d => x(d.year))
            .attr("cy", d => y(yValue(d)))
            .attr("r", 5)
            .attr("fill", color);

        // Vẽ Label trên chấm
        svg.selectAll(".label")
            .data(validData)
            .enter().append("text")
            .attr("x", d => x(d.year))
            .attr("y", d => y(yValue(d)) - 10)
            .attr("text-anchor", "middle")
            .style("font-size", "11px")
            .style("font-weight", "bold")
            .style("fill", color)
            .text(d => {
                const val = yValue(d);
                return isPercent ? val.toFixed(2) + '%' : val.toFixed(2);
            });
    }

    // --- SIMPLE BAR CHART (Dùng riêng cho EPS) ---
    function drawSimpleBarChart(selector, data, key, color) {
        const { svg, width, height } = setupCanvas(selector);
        
        const validData = data.filter(d => d[key] !== null);

        // Trục X
        const x = d3.scaleBand()
            .domain(validData.map(d => d.year))
            .range([0, width])
            .padding(0.4);
            
        svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x));

        // Trục Y
        const yMax = d3.max(validData, d => d[key]);
        const y = d3.scaleLinear()
            .domain([0, (yMax || 1000) * 1.1])
            .range([height, 0]);

        // Format trục Y cho EPS (ví dụ 1,000)
        svg.append("g").call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2s")));

        // Vẽ cột
        svg.selectAll(".bar")
            .data(validData)
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", d => x(d.year))
            .attr("width", x.bandwidth())
            .attr("y", d => y(d[key]))
            .attr("height", d => height - y(d[key]))
            .attr("fill", color)
            .attr("rx", 2);

        // Label trên cột
        svg.selectAll(".label")
            .data(validData)
            .enter().append("text")
            .attr("x", d => x(d.year) + x.bandwidth() / 2)
            .attr("y", d => y(d[key]) - 5)
            .attr("text-anchor", "middle")
            .style("font-size", "10px")
            .style("fill", "#333")
            .text(d => d3.format(",.0f")(d[key])); // Format số nguyên có dấu phẩy (2,500)
    }

});