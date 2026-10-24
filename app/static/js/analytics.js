/**
 * CIVICFIX — CHART.JS ANALYTICS DASHBOARD
 * Responsive visual intelligence: Department Workload, Categories, Severity, Resolution Velocity
 */

document.addEventListener('DOMContentLoaded', () => {
  initAnalyticsCharts();
});

function initAnalyticsCharts() {
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  const textColor = isDark ? '#94A3B8' : '#475569';
  const gridColor = isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(203, 213, 225, 0.6)';

  Chart.defaults.color = textColor;
  Chart.defaults.font.family = "'Inter', sans-serif";

  // 1. Department Workload Chart
  const deptCtx = document.getElementById('deptWorkloadChart');
  if (deptCtx && window.deptStatsData) {
    new Chart(deptCtx, {
      type: 'bar',
      data: {
        labels: window.deptStatsData.map(d => d.name.split(',')[0]),
        datasets: [
          {
            label: 'Total Reports',
            data: window.deptStatsData.map(d => d.total_issues),
            backgroundColor: 'rgba(34, 211, 238, 0.6)',
            borderColor: '#22D3EE',
            borderWidth: 1.5,
            borderRadius: 6
          },
          {
            label: 'Resolved',
            data: window.deptStatsData.map(d => d.resolved_count),
            backgroundColor: 'rgba(52, 211, 153, 0.7)',
            borderColor: '#34D399',
            borderWidth: 1.5,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: gridColor } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        },
        plugins: {
          legend: { position: 'top' }
        }
      }
    });
  }

  // 2. Category Distribution Doughnut Chart
  const catCtx = document.getElementById('categoryDoughnutChart');
  if (catCtx && window.catStatsData) {
    const palette = ['#22D3EE', '#8B5CF6', '#2DD4BF', '#FBBF24', '#FB7185', '#38BDF8', '#A78BFA', '#94A3B8'];
    new Chart(catCtx, {
      type: 'doughnut',
      data: {
        labels: window.catStatsData.map(c => c.category),
        datasets: [{
          data: window.catStatsData.map(c => c.count),
          backgroundColor: palette.slice(0, window.catStatsData.length),
          borderWidth: 2,
          borderColor: isDark ? '#171A3A' : '#FFFFFF'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });
  }

  // 3. Severity Distribution
  const sevCtx = document.getElementById('severityChart');
  if (sevCtx && window.sevStatsData) {
    const sevColors = {
      'Critical': '#FB7185',
      'High': '#FBBF24',
      'Medium': '#22D3EE',
      'Low': '#94A3B8'
    };
    new Chart(sevCtx, {
      type: 'polarArea',
      data: {
        labels: window.sevStatsData.map(s => s.severity),
        datasets: [{
          data: window.sevStatsData.map(s => s.count),
          backgroundColor: window.sevStatsData.map(s => sevColors[s.severity] || '#94A3B8'),
          borderWidth: 1.5,
          borderColor: isDark ? '#171A3A' : '#FFFFFF'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top' }
        }
      }
    });
  }

  // 4. Monthly/Weekly Trends
  const trendCtx = document.getElementById('trendLineChart');
  if (trendCtx) {
    new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7 (Today)'],
        datasets: [
          {
            label: 'Reported Issues',
            data: [3, 5, 4, 8, 6, 7, 6],
            borderColor: '#22D3EE',
            backgroundColor: 'rgba(34, 211, 238, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: 'Resolved Issues',
            data: [1, 2, 3, 5, 4, 6, 5],
            borderColor: '#34D399',
            backgroundColor: 'rgba(52, 211, 153, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: gridColor } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        }
      }
    });
  }
}
