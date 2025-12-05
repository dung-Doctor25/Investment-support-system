document.addEventListener('DOMContentLoaded', function () {
    const API_URL = '/api/financial-ratios/'; // Đường dẫn API của bạn

    let globalData = null;

    // --- 1. FETCH DATA ---
    fetch(API_URL)
        .then(response => response.json())
        .then(data => {
            globalData = data;
            console.log("Fetched data:", data);
            initDashboard(data);
        })
        .catch(error => console.error('Error fetching data:', error));

    // --- 2. INITIALIZE ---
    function initDashboard(data) {
        const stockSelect = document.getElementById('stock-select');
        const stockCodes = Object.keys(data);
        console.log("Available stock codes:", stockCodes);
        // Populate Dropdown
        stockCodes.forEach(code => {
            const option = document.createElement('option');
            option.value = code;
            option.text = code;
            stockSelect.appendChild(option);
        });

        // Mặc định chọn mã đầu tiên (ví dụ SCS)
        if (stockCodes.length > 0) {
            updateCharts(stockCodes[0]);
        }

        // Sự kiện đổi mã cổ phiếu
        stockSelect.addEventListener('change', function () {
            updateCharts(this.value);
        });
    }

    // --- 3. UPDATE CHARTS ---
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
        // Chuyển đổi dữ liệu object {year: {metrics}} thành array [{year, metrics}]
        // và sắp xếp theo năm
        const chartData = Object.entries(companyData.annual_reports)
            .map(([year, metrics]) => ({
                year: year,
                ...metrics
            }))
            .sort((a, b) => a.year - b.year);

        // Cập nhật KPI (lấy năm gần nhất có dữ liệu)
        updateKPIs(chartData);

        // Vẽ các biểu đồ
        drawLineChart('#chart-roa-roe', chartData, ['ROA', 'ROE'], ['#0d47a1', '#42a5f5']);
        drawSingleLineChart('#chart-liquidity', chartData, 'TySuatThanhToanHienHanh', '#0d47a1');
        drawStackedBarChart('#chart-assets', chartData); // Dựa trên HeSoNoTrenTongTaiSan
        drawGrowthChart('#chart-growth', chartData);     // Tăng trưởng tài sản & Lợi nhuận
    }

    // --- 4. UPDATE KPI CARDS ---
    // --- 4. UPDATE KPI CARDS (Dạng Bar Chart 1 cột năm cuối) ---
    function updateKPIs(data) {
        // data: [{year: '2020', ROA: ...}, {year: '2021', ...}]
        
        drawKpiChart('#kpi-roa', data, 'ROA', true);
        drawKpiChart('#kpi-roe', data, 'ROE', true);
        drawKpiChart('#kpi-current-ratio', data, 'TySuatThanhToanHienHanh', false);
        drawKpiChart('#kpi-dept', data, 'HeSoNoTrenTongTaiSan', true);
    }

    function drawKpiChart(selector, data, key, isPercent) {
        // 1. Xóa nội dung cũ
        const container = d3.select(selector);
        container.html(""); 

        // 2. Thiết lập kích thước
        const width = document.querySelector(selector).clientWidth;
        const height = document.querySelector(selector).clientHeight;
        
        // Khoảng cách dành cho Text trục X ở dưới đáy
        const paddingBottom = 20; 
        const chartHeight = height - paddingBottom;

        // Tạo SVG
        const svg = container.append("svg")
            .attr("width", width)
            .attr("height", height);

        // 3. Xử lý dữ liệu
        // Lấy giá trị mới nhất để hiển thị Text Big Number
        const latestItem = data[data.length - 1];
        const latestValue = latestItem ? latestItem[key] : 0;

        // Lọc dữ liệu sạch để tính toán Scale (Toàn bộ lịch sử)
        const validData = data.map(d => ({
            year: d.year,
            value: d[key] === null ? 0 : d[key]
        }));

        // QUAN TRỌNG: Chỉ lấy năm cuối cùng để vẽ cột
        const finalYearData = validData.length > 0 ? [validData[validData.length - 1]] : [];

        // 4. Tạo Scales (Tỷ lệ)
        // Domain trục X chỉ chứa năm cuối cùng
        const x = d3.scaleBand()
            .domain(finalYearData.map(d => d.year))
            .range([0, width])
            .padding(0.3); // Tăng padding để cột không quá bè

        // Domain trục Y vẫn tính trên TOÀN BỘ dữ liệu (để cột có độ cao tương đối chính xác)
        // Nếu chỉ tính trên năm cuối, cột sẽ luôn full chiều cao (trông không hợp lý)
        const yMax = d3.max(validData, d => d.value) || 1; 
        const y = d3.scaleLinear()
            .domain([0, yMax * 1.2]) 
            .range([chartHeight, 0]);

        // 5. Vẽ Trục X (Hiển thị Text, ẩn đường trục)
        const xAxis = svg.append("g")
            .attr("transform", `translate(0, ${chartHeight})`) // Đưa xuống đáy vùng vẽ
            .call(d3.axisBottom(x).tickSize(0)); // tickSize(0) ẩn vạch chia

        // Tùy chỉnh CSS cho trục X
        xAxis.select(".domain").remove(); // Ẩn đường kẻ ngang trục X
        xAxis.selectAll("text")
            .style("font-size", "12px")
            .style("font-weight", "500")
            .style("fill", "#5f5a5aff") // Màu chữ trục X (đổi thành đen nếu nền trắng)
            .attr("dy", "10"); // Đẩy chữ xuống một chút cho thoáng

        // 6. Vẽ Cột (Chỉ 1 cột năm cuối)
        svg.selectAll(".bar")
            .data(finalYearData) // Chỉ bind dữ liệu năm cuối
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", d => x(d.year))
            .attr("width", x.bandwidth())
            .attr("y", d => y(d.value))
            .attr("height", d => chartHeight - y(d.value))
            .attr("fill", "#0f2b4a") // Màu cột
            .attr("rx", 4); // Bo tròn góc

        // 7. Hiển thị Con số lớn (Big Number)
        const formattedValue = isPercent 
            ? (latestValue * 100).toFixed(2) + '%' 
            : latestValue.toFixed(2);

        svg.append("text")
            .attr("x", width / 2)
            .attr("y", chartHeight / 2) // Căn giữa theo vùng vẽ biểu đồ
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .style("font-size", "20px")
            .style("font-weight", "bold")
            .style("fill", "#333") // Màu chữ số liệu
            .style(
            "text-shadow",
            "0px 0px 4px rgba(255,255,255,0.9), \
            2px 2px 4px rgba(255,255,255,0.9), \
            -2px -2px 4px rgba(255,255,255,0.9), \
            2px -2px 4px rgba(255,255,255,0.9), \
            -2px 2px 4px rgba(255,255,255,0.9)"
            )
            .text(formattedValue);
            
        // Tooltip đơn giản
        svg.selectAll("rect")
            .append("title")
            .text(d => `Năm ${d.year}: ${isPercent ? (d.value*100).toFixed(2)+'%' : d.value.toFixed(2)}`);
    }

    // ============================================================
    // D3.JS CHART FUNCTIONS
    // ============================================================

    // Setup chung cho D3
    function setupCanvas(selector) {
        d3.select(selector).selectAll("*").remove(); // Xóa chart cũ
        const container = document.querySelector(selector);
        const width = container.clientWidth;
        const height = container.clientHeight-10;
        const margin = { top: 20, right: 30, bottom: 30, left: 40 };

        const svg = d3.select(selector)
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        return { svg, width: width - margin.left - margin.right, height: height - margin.top - margin.bottom };
    }

    // --- Chart 1: Multi-line Chart (ROA, ROE) ---
    function drawLineChart(selector, data, keys, colors) {
        const { svg, width, height } = setupCanvas(selector);

        // X Axis
        const x = d3.scalePoint()
            .domain(data.map(d => d.year))
            .range([0, width]);
        svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));

        // Y Axis (Tính % nên nhân 100 để hiển thị cho đẹp)
        const y = d3.scaleLinear()
            .domain([d3.min(data, d => Math.min((d[keys[0]]||0)*100, (d[keys[1]]||0)*100)) - 5, 
                     d3.max(data, d => Math.max((d[keys[0]]||0)*100, (d[keys[1]]||0)*100)) + 5])
            .range([height, 25]);
        

        // Line Generator
        keys.forEach((key, index) => {
            // Filter null data
            const validData = data.filter(d => d[key] !== null);

            const line = d3.line()
                .x(d => x(d.year))
                .y(d => y(d[key] * 100));

            svg.append("path")
                .datum(validData)
                .attr("fill", "none")
                .attr("stroke", colors[index])
                .attr("stroke-width", 2)
                .attr("d", line);

            // Dots
            svg.selectAll(".dot-" + key)
                .data(validData)
                .enter().append("circle")
                .attr("cx", d => x(d.year))
                .attr("cy", d => y(d[key] * 100))
                .attr("r", 4)
                .attr("fill", colors[index])
                .append("title") // Tooltip đơn giản
                .text(d => `${key}: ${(d[key]*100).toFixed(2)}%`);
            // --- PHẦN THÊM LABEL ---
            svg.selectAll(".label-" + key)
                .data(validData)
                .enter().append("text")
                .attr("x", d => x(d.year))
                .attr("y", d => y(d[key] * 100) - 10) // Đẩy lên trên điểm tròn 10px
                .attr("text-anchor", "middle") // Căn giữa text so với điểm
                .style("font-size", "11px")
                .style("font-weight", "bold")
                .style("fill", colors[index]) // Màu chữ giống màu đường
                .text(d => `${(d[key] * 100).toFixed(2)}%`); // Hiển thị 2 số thập phân                
        });
        // --- PHẦN THÊM LEGEND (CHÚ THÍCH HÀNG NGANG) ---
        
        // 1. Cấu hình khoảng cách
        const itemSpacing = 100; // Khoảng cách giữa các mục (pixel)
        const totalLegendWidth = keys.length * itemSpacing; // Tổng chiều rộng dự kiến

        // 2. Tạo nhóm legend tổng
        const legend = svg.append("g")
            .attr("class", "legend")
            // Logic vị trí: 
            // x = width - totalLegendWidth (để căn lề phải tổng thể)
            // y = -30 (đưa lên trên biểu đồ)
            .attr("transform", `translate(${width - totalLegendWidth }, -10)`);

        // 3. Tạo các nhóm con
        const legendGroups = legend.selectAll("g")
            .data(keys)
            .enter().append("g")
            // QUAN TRỌNG: Dịch chuyển theo trục X (ngang) thay vì trục Y
            .attr("transform", (d, i) => `translate(${i * itemSpacing}, 0)`);

        // 4. Vẽ ô vuông màu (Đặt bên trái)
        legendGroups.append("rect")
            .attr("width", 15)
            .attr("height", 15)
            .attr("fill", (d, i) => colors[i])
            .attr("rx", 2);

        // 5. Vẽ Text tên chỉ số (Đặt bên phải ô vuông)
        legendGroups.append("text")
            .attr("x", 20) // Cách lề trái 20px (để không đè lên ô vuông 15px)
            .attr("y", 9.5) 
            .attr("dy", "0.32em")
            .style("font-size", "12px")
            .style("font-weight", "500")
            .style("fill", "#333")
            .style("text-anchor", "start") // Căn trái: Text sẽ chạy từ ô vuông ra phía sau
            .text(d => d);
    }

    // --- Chart 2: Single Line/Dot Chart (Liquidity) ---
    function drawSingleLineChart(selector, data, key, color) {
        const { svg, width, height } = setupCanvas(selector);
        
        const validData = data.filter(d => d[key] !== null);

        const x = d3.scalePoint().domain(data.map(d => d.year)).range([0, width]).padding(0.5);
        svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));

        const y = d3.scaleLinear()
            .domain([0, d3.max(validData, d => d[key]) * 1.2])
            .range([height, 25]);
        

        // Vẽ đường kết nối
        svg.append("path")
            .datum(validData)
            .attr("fill", "none")
            .attr("stroke", "#b0bec5") // Màu xám nhạt cho đường nối
            .attr("stroke-width", 1)
            .attr("d", d3.line().x(d => x(d.year)).y(d => y(d[key])));

        // Vẽ chấm tròn lớn (Big Dots)
        svg.selectAll("circle")
            .data(validData)
            .enter().append("circle")
            .attr("cx", d => x(d.year))
            .attr("cy", d => y(d[key]))
            .attr("r", 6)
            .attr("fill", color);

        // Label text trên chấm
        svg.selectAll(".label")
            .data(validData)
            .enter().append("text")
            .attr("x", d => x(d.year))
            .attr("y", d => y(d[key]) - 10)
            .attr("text-anchor", "middle")
            .style("font-size", "10px")
            .style("font-weight", "bold")
            .style("fill", color)
            .text(d => d[key].toFixed(2));

        // --- PHẦN THÊM LEGEND (GÓC PHẢI TRÊN) ---
        // Vì chỉ có 1 item, ta neo nó vào sát lề phải (width)
        const legend = svg.append("g")
            .attr("class", "legend")
            .attr("transform", `translate(${width}, -10)`); // Đưa lên trên biểu đồ và sát lề phải

        // A. Vẽ ô vuông màu (Nằm sát mép phải)
        legend.append("rect")
            .attr("x", -15) // Vẽ từ vị trí -15 lùi về 0
            .attr("width", 15)
            .attr("height", 15)
            .attr("fill", color)
            .attr("rx", 2);

        // B. Vẽ Text tên chỉ số (Nằm bên trái ô vuông)
        legend.append("text")
            .attr("x", -20) // Cách ô vuông 5px
            .attr("y", 9.5)
            .attr("dy", "0.32em")
            .style("font-size", "12px")
            .style("font-weight", "500")
            .style("fill", "#333")
            .style("text-anchor", "end") // QUAN TRỌNG: Căn đuôi text chạm vào mốc x=-20
            .text('Tỷ suất thanh toán hiện hành'); // Hiển thị tên (ví dụ: TySuatThanhToan)
    }

 // --- Chart 3: 100% Stacked Bar Chart (Debt vs Equity) ---
    function drawStackedBarChart(selector, data) {
        const { svg, width, height } = setupCanvas(selector);
        
        // Xử lý data
        const stackData = data.map(d => {
            if (d.HeSoNoTrenTongTaiSan === null) return null;
            return {
                year: d.year,
                debt: d.HeSoNoTrenTongTaiSan * 100,
                equity: (1 - d.HeSoNoTrenTongTaiSan) * 100
            };
        }).filter(d => d !== null);

        const subgroups = ["debt", "equity"];
        const groups = stackData.map(d => d.year);

        // X Axis
        const x = d3.scaleBand().domain(groups).range([0, width]).padding(0.2);
        svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));

        // Y Axis
        const y = d3.scaleLinear().domain([0, 100]).range([height, 25]);
        

        const color = d3.scaleOrdinal().domain(subgroups).range(['#0d47a1', '#4fc3f7']);

        const stackedData = d3.stack().keys(subgroups)(stackData);

        // Tạo nhóm (Group) cho từng lớp dữ liệu
        const series = svg.append("g")
            .selectAll("g")
            .data(stackedData)
            .enter().append("g")
            .attr("fill", d => color(d.key));

        // 1. Vẽ các Cột (Rects)
        series.selectAll("rect")
            .data(d => d)
            .enter().append("rect")
            .attr("x", d => x(d.data.year))
            .attr("y", d => y(d[1]))
            .attr("height", d => y(d[0]) - y(d[1]))
            .attr("width", x.bandwidth())
            .append("title") // Tooltip mặc định
            .text(d => `${(d[1]-d[0]).toFixed(1)}%`);

        // 2. Vẽ Nhãn (Labels) - Phần thêm mới
        series.selectAll("text")
            .data(d => d)
            .enter().append("text")
            .attr("x", d => x(d.data.year) + x.bandwidth() / 2) // Căn giữa chiều ngang
            .attr("y", d => y(d[1]) + (y(d[0]) - y(d[1])) / 2) // Căn giữa chiều dọc đoạn cột
            .attr("dy", "0.35em") // Căn chỉnh vertical alignment
            .attr("text-anchor", "middle")
            .style("fill", "white") // Màu chữ trắng
            .style("font-size", "11px")
            .style("font-weight", "bold")
            .style("pointer-events", "none") // Để chuột xuyên qua text xuống tooltip của rect
            .text(d => {
                const val = d[1] - d[0];
                // Chỉ hiển thị nếu giá trị > 5% để tránh chữ bị chồng chéo khi cột quá bé
                return val > 5 ? val.toFixed(1) + '%' : ''; 
            });
        // --- 5. PHẦN THÊM LEGEND (GÓC PHẢI TRÊN - HÀNG NGANG) ---
        
        // Mapping tên hiển thị (Key code -> Tên tiếng Việt)
        const labelMap = {
            "debt": "Nợ phải trả",
            "equity": "Vốn chủ sở hữu"
        };

        // Cấu hình vị trí
        const itemSpacing = 120; // Khoảng cách giữa các mục legend
        const legendWidth = subgroups.length * itemSpacing; 
        
        // Tạo group legend tổng
        const legend = svg.append("g")
            .attr("class", "legend")
            // Dịch chuyển về góc phải trên, chừa lề phải 10px
            .attr("transform", `translate(${width - legendWidth + 30}, -10)`);

        // Tạo từng item trong legend
        const legendItems = legend.selectAll("g")
            .data(subgroups) // ["debt", "equity"]
            .enter().append("g")
            .attr("transform", (d, i) => `translate(${(i * itemSpacing)+10}, 0)`);

        // A. Vẽ ô vuông màu
        legendItems.append("rect")
            .attr("width", 15)
            .attr("height", 15)
            .attr("fill", d => color(d))
            .attr("rx", 2);

        // B. Vẽ tên chú thích
        legendItems.append("text")
            .attr("x", 20) // Cách ô vuông 5px
            .attr("y", 9.5)
            .attr("dy", "0.32em")
            .style("font-size", "12px")
            .style("font-weight", "500")
            .style("fill", "#333")
            .style("text-anchor", "start")
            .text(d => labelMap[d]); // Lấy tên tiếng Việt từ map
    }

    // --- Chart 4: Growth Chart (Multi-line with Zero line) ---
    function drawGrowthChart(selector, data) {
        const { svg, width, height } = setupCanvas(selector);
        const keys = ['TangTruongLoiNhuan', 'TangTruongTaiSan'];
        const colors = ['#0d47a1', '#4fc3f7']; // Xanh đậm (LN), Xanh nhạt (TS)

        const validData = data.filter(d => d[keys[0]] !== null && d[keys[1]] !== null);

        const x = d3.scalePoint().domain(data.map(d => d.year)).range([0, width]);
        svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));

        // Tìm min/max để vẽ trục Y (bao gồm số âm)
        const yMin = d3.min(validData, d => Math.min(d[keys[0]], d[keys[1]]));
        const yMax = d3.max(validData, d => Math.max(d[keys[0]], d[keys[1]]));
        
        const y = d3.scaleLinear()
            .domain([yMin < 0 ? yMin : 0, yMax])
            .range([height, 25]);
        
       

        // Vẽ đường 0% (Zero line)
        svg.append("line")
            .attr("x1", 0)
            .attr("x2", width)
            .attr("y1", y(0))
            .attr("y2", y(0))
            .attr("stroke", "#999")
            .attr("stroke-width", 1)
            .attr("stroke-dasharray", "4");

        keys.forEach((key, index) => {
            const line = d3.line()
                .x(d => x(d.year))
                .y(d => y(d[key]));

            svg.append("path")
                .datum(validData)
                .attr("fill", "none")
                .attr("stroke", colors[index])
                .attr("stroke-width", 2)
                .attr("d", line);
            
            // Dots
            svg.selectAll(".dot-growth-" + index)
                .data(validData)
                .enter().append("circle")
                .attr("cx", d => x(d.year))
                .attr("cy", d => y(d[key]))
                .attr("r", 4)
                .attr("fill", colors[index])
                .append("title")
                .text(d => `${key}: ${(d[key]*100).toFixed(2)}%`);
            // --- PHẦN THÊM LABEL ---
            svg.selectAll(".label-growth-" + index)
                .data(validData)
                .enter().append("text")
                .attr("x", d => x(d.year))
                .attr("y", d => y(d[key]) - 10) // Đẩy lên trên điểm tròn 10px
                .attr("text-anchor", "middle") // Căn giữa text so với điểm
                .style("font-size", "11px")
                .style("font-weight", "bold")
                .style("fill", colors[index]) // Màu chữ giống màu đường
                .text(d => `${(d[key] * 100).toFixed(2)}%`); // Hiển thị 2 số thập phân
        });
        // --- PHẦN THÊM LEGEND (HÀNG NGANG - GÓC PHẢI TRÊN) ---
        
        // 1. Map tên tiếng Việt
        const labelMap = {
            'TangTruongLoiNhuan': 'Tăng trưởng Lợi nhuận',
            'TangTruongTaiSan': 'Tăng trưởng Tài sản'
        };

        // 2. Cấu hình vị trí
        const itemSpacing = 160; // Khoảng cách rộng hơn vì tên dài
        const legendWidth = keys.length * itemSpacing;

        // 3. Tạo nhóm Legend
        const legend = svg.append("g")
            .attr("class", "legend")
            .attr("transform", `translate(${width - legendWidth + 30}, -20)`);

        const legendItems = legend.selectAll("g")
            .data(keys)
            .enter().append("g")
            .attr("transform", (d, i) => `translate(${i * itemSpacing}, 0)`);

        // Vẽ ô màu
        legendItems.append("rect")
            .attr("width", 15)
            .attr("height", 15)
            .attr("fill", (d, i) => colors[i])
            .attr("rx", 2);

        // Vẽ tên
        legendItems.append("text")
            .attr("x", 20)
            .attr("y", 9.5)
            .attr("dy", "0.32em")
            .style("font-size", "12px")
            .style("font-weight", "500")
            .style("fill", "#333")
            .style("text-anchor", "start")
            .text(d => labelMap[d]);
    }
});