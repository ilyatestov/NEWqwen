<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSS Sentinel - Dashboard</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        h1 { color: #00d9ff; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 2em; font-weight: bold; color: #00d9ff; }
        .stat-label { color: #888; margin-top: 5px; }
        .panel { background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .panel h2 { color: #00d9ff; margin-bottom: 15px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #aaa; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #333; border-radius: 5px; background: #0f3460; color: #eee; }
        button { background: #00d9ff; color: #000; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        button:hover { background: #00b8d4; }
        button.danger { background: #e94560; color: #fff; }
        button.danger:hover { background: #c73e54; }
        .feed-list { list-style: none; }
        .feed-item { background: #0f3460; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .feed-info { flex: 1; }
        .feed-title { font-weight: bold; color: #00d9ff; }
        .feed-url { font-size: 0.9em; color: #888; margin-top: 5px; }
        .feed-actions { display: flex; gap: 10px; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; margin-left: 10px; }
        .badge.active { background: #00c853; color: #000; }
        .badge.inactive { background: #e94560; color: #fff; }
        .chart-container { position: relative; height: 300px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #0f3460; border: none; color: #eee; cursor: pointer; border-radius: 5px; }
        .tab.active { background: #00d9ff; color: #000; }
        .hidden { display: none; }
        .alert { padding: 15px; border-radius: 5px; margin-bottom: 15px; }
        .alert.success { background: #00c853; color: #000; }
        .alert.error { background: #e94560; color: #fff; }
        textarea { min-height: 100px; font-family: monospace; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .checkbox-group input { width: auto; }
    </style>
</head>
<body>
<div id="app" class="container">
    <header>
        <h1>🛡️ RSS Sentinel</h1>
        <div>
            <button @click="refreshData">🔄 Refresh</button>
        </div>
    </header>

    <!-- Alert Messages -->
    <div v-if="message" :class="'alert ' + messageType">{{ message }}</div>

    <!-- Statistics -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{{ stats.total_feeds || 0 }}</div>
            <div class="stat-label">Total Feeds</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ stats.active_feeds || 0 }}</div>
            <div class="stat-label">Active Feeds</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ stats.published_entries || 0 }}</div>
            <div class="stat-label">Published</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ stats.filtered_entries || 0 }}</div>
            <div class="stat-label">Filtered</div>
        </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
        <button class="tab" :class="{active: currentTab === 'feeds'}" @click="currentTab = 'feeds'">📡 Feeds</button>
        <button class="tab" :class="{active: currentTab === 'add'}" @click="currentTab = 'add'">➕ Add Feed</button>
        <button class="tab" :class="{active: currentTab === 'filter'}" @click="currentTab = 'filter'">🔍 Filter Preview</button>
        <button class="tab" :class="{active: currentTab === 'chart'}" @click="currentTab = 'chart'">📊 Analytics</button>
    </div>

    <!-- Feeds List -->
    <div v-show="currentTab === 'feeds'" class="panel">
        <h2>Your RSS Feeds</h2>
        <ul class="feed-list">
            <li v-for="feed in feeds" :key="feed.id" class="feed-item">
                <div class="feed-info">
                    <div class="feed-title">{{ feed.title || 'Untitled' }} <span :class="'badge ' + (feed.is_active ? 'active' : 'inactive')">{{ feed.is_active ? 'Active' : 'Inactive' }}</span></div>
                    <div class="feed-url">{{ feed.url }}</div>
                    <div style="font-size: 0.85em; color: #666; margin-top: 5px;">
                        Check: {{ feed.check_interval }}s | 
                        Include: {{ feed.filter_keywords_include.join(', ') || 'none' }} | 
                        Exclude: {{ feed.filter_keywords_exclude.join(', ') || 'none' }}
                    </div>
                </div>
                <div class="feed-actions">
                    <button @click="toggleFeed(feed)">⏯️</button>
                    <button @click="editFeed(feed)">✏️</button>
                    <button class="danger" @click="deleteFeed(feed.id)">🗑️</button>
                </div>
            </li>
            <li v-if="feeds.length === 0" style="text-align: center; color: #666; padding: 20px;">No feeds yet. Add your first RSS feed!</li>
        </ul>
    </div>

    <!-- Add Feed Form -->
    <div v-show="currentTab === 'add'" class="panel">
        <h2>Add New RSS Feed</h2>
        <form @submit.prevent="addFeed">
            <div class="form-group">
                <label>RSS URL *</label>
                <input v-model="newFeed.url" type="url" required placeholder="https://example.com/rss">
            </div>
            <div class="form-group">
                <label>Title (optional)</label>
                <input v-model="newFeed.title" type="text" placeholder="My News Feed">
            </div>
            <div class="form-group">
                <label>Check Interval (seconds)</label>
                <input v-model.number="newFeed.check_interval" type="number" min="60" step="60" value="300">
            </div>
            <div class="form-group">
                <label>Include Keywords (comma-separated) - at least one must match</label>
                <input v-model="newFeed.filter_keywords_include" type="text" placeholder="ai, machine learning, tech">
            </div>
            <div class="form-group">
                <label>Exclude Keywords (comma-separated) - will be filtered out</label>
                <input v-model="newFeed.filter_keywords_exclude" type="text" placeholder="spam, advertisement, clickbait">
            </div>
            <div class="form-group">
                <label>Minimum Content Length</label>
                <input v-model.number="newFeed.filter_min_length" type="number" min="10" value="50">
            </div>
            <div class="form-group">
                <label>Post Template</label>
                <textarea v-model="newFeed.post_template" placeholder="{title}&#10;&#10;{content}&#10;&#10;{link}"></textarea>
            </div>
            <div class="form-group checkbox-group">
                <input v-model="newFeed.telegram_enabled" type="checkbox" id="tg_enabled">
                <label for="tg_enabled">Enable Telegram Publishing</label>
            </div>
            <button type="submit">➕ Add Feed</button>
        </form>
    </div>

    <!-- Filter Preview -->
    <div v-show="currentTab === 'filter'" class="panel">
        <h2>Filter Preview</h2>
        <p style="color: #888; margin-bottom: 15px;">Test how your filters will work on sample content</p>
        <div class="form-group">
            <label>Title</label>
            <input v-model="preview.title" type="text" placeholder="Article title">
        </div>
        <div class="form-group">
            <label>Content</label>
            <textarea v-model="preview.content" placeholder="Article content..."></textarea>
        </div>
        <div class="form-group">
            <label>Link</label>
            <input v-model="preview.link" type="url" placeholder="https://example.com/article">
        </div>
        <div class="form-group">
            <label>Include Keywords</label>
            <input v-model="preview.filter_keywords_include" type="text" placeholder="ai, tech">
        </div>
        <div class="form-group">
            <label>Exclude Keywords</label>
            <input v-model="preview.filter_keywords_exclude" type="text" placeholder="spam, ads">
        </div>
        <button @click="testFilter">🧪 Test Filter</button>
        
        <div v-if="previewResult" style="margin-top: 20px; padding: 15px; background: #0f3460; border-radius: 5px;">
            <h3>Result:</h3>
            <div :style="{color: previewResult.should_publish ? '#00c853' : '#e94560', fontWeight: 'bold', marginTop: '10px'}">
                {{ previewResult.should_publish ? '✅ Will be published' : '❌ Will be filtered' }}
            </div>
            <div v-if="previewResult.filtered_reason" style="color: #e94560; margin-top: 5px;">Reason: {{ previewResult.filtered_reason }}</div>
            <div v-if="previewResult.images && previewResult.images.length" style="margin-top: 10px;">
                <strong>Images found:</strong> {{ previewResult.images.length }}
            </div>
            <div v-if="previewResult.relevance_score" style="margin-top: 5px;">
                <strong>Relevance Score:</strong> {{ (previewResult.relevance_score * 100).toFixed(1) }}%
            </div>
        </div>
    </div>

    <!-- Analytics Chart -->
    <div v-show="currentTab === 'chart'" class="panel">
        <h2>Activity (Last 7 Days)</h2>
        <div class="chart-container">
            <canvas id="activityChart"></canvas>
        </div>
    </div>
</div>

<script>
const { createApp } = Vue;

createApp({
    data() {
        return {
            apiBase: '',
            currentTab: 'feeds',
            message: '',
            messageType: 'success',
            stats: {},
            feeds: [],
            newFeed: {
                url: '',
                title: '',
                check_interval: 300,
                filter_keywords_include: '',
                filter_keywords_exclude: '',
                filter_min_length: 50,
                post_template: '{title}\\n\\n{content}\\n\\n{link}',
                telegram_enabled: true
            },
            preview: {
                title: '',
                content: '',
                link: '',
                filter_keywords_include: '',
                filter_keywords_exclude: ''
            },
            previewResult: null,
            chart: null
        };
    },
    mounted() {
        this.refreshData();
    },
    methods: {
        async refreshData() {
            await this.loadStats();
            await this.loadFeeds();
            if (this.currentTab === 'chart') {
                this.renderChart();
            }
        },
        async loadStats() {
            try {
                const res = await fetch(`${this.apiBase}/api/stats`);
                this.stats = await res.json();
            } catch (e) {
                console.error('Failed to load stats:', e);
            }
        },
        async loadFeeds() {
            try {
                const res = await fetch(`${this.apiBase}/api/feeds`);
                this.feeds = await res.json();
            } catch (e) {
                console.error('Failed to load feeds:', e);
            }
        },
        showMessage(msg, type = 'success') {
            this.message = msg;
            this.messageType = type;
            setTimeout(() => this.message = '', 3000);
        },
        async addFeed() {
            const params = new URLSearchParams({
                url: this.newFeed.url,
                title: this.newFeed.title,
                check_interval: this.newFeed.check_interval,
                filter_keywords_include: this.newFeed.filter_keywords_include.split(',').map(s => s.trim()).filter(Boolean),
                filter_keywords_exclude: this.newFeed.filter_keywords_exclude.split(',').map(s => s.trim()).filter(Boolean),
                filter_min_length: this.newFeed.filter_min_length,
                post_template: this.newFeed.post_template,
                telegram_enabled: this.newFeed.telegram_enabled
            });
            
            try {
                const res = await fetch(`${this.apiBase}/api/feeds?${params}`, { method: 'POST' });
                if (!res.ok) throw new Error(await res.text());
                this.showMessage('Feed added successfully!');
                this.newFeed = { url: '', title: '', check_interval: 300, filter_keywords_include: '', filter_keywords_exclude: '', filter_min_length: 50, post_template: '{title}\\n\\n{content}\\n\\n{link}', telegram_enabled: true };
                this.currentTab = 'feeds';
                await this.loadFeeds();
                await this.loadStats();
            } catch (e) {
                this.showMessage(e.message, 'error');
            }
        },
        async deleteFeed(id) {
            if (!confirm('Are you sure you want to delete this feed?')) return;
            try {
                await fetch(`${this.apiBase}/api/feeds/${id}`, { method: 'DELETE' });
                this.showMessage('Feed deleted!');
                await this.loadFeeds();
                await this.loadStats();
            } catch (e) {
                this.showMessage('Failed to delete feed', 'error');
            }
        },
        async toggleFeed(feed) {
            try {
                await fetch(`${this.apiBase}/api/feeds/${feed.id}/toggle`, { method: 'PUT' });
                feed.is_active = !feed.is_active;
                this.showMessage(`Feed ${feed.is_active ? 'activated' : 'deactivated'}`);
            } catch (e) {
                this.showMessage('Failed to toggle feed', 'error');
            }
        },
        editFeed(feed) {
            // Simple prompt-based editing (can be enhanced with modal)
            const newTitle = prompt('Edit title:', feed.title);
            if (newTitle !== null) {
                feed.title = newTitle;
                // TODO: Save to server
            }
        },
        async testFilter() {
            const params = new URLSearchParams({
                title: this.preview.title,
                content: this.preview.content,
                link: this.preview.link,
                filter_keywords_include: this.preview.filter_keywords_include.split(',').map(s => s.trim()).filter(Boolean),
                filter_keywords_exclude: this.preview.filter_keywords_exclude.split(',').map(s => s.trim()).filter(Boolean),
                filter_min_length: 50
            });
            
            try {
                const res = await fetch(`${this.apiBase}/api/filter/preview?${params}`, { method: 'POST' });
                this.previewResult = await res.json();
            } catch (e) {
                this.showMessage('Failed to test filter', 'error');
            }
        },
        renderChart() {
            const ctx = document.getElementById('activityChart');
            if (!ctx) return;
            
            if (this.chart) this.chart.destroy();
            
            const labels = Object.keys(this.stats.daily_stats || {}).sort();
            const data = labels.map(d => this.stats.daily_stats[d]);
            
            this.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Entries Processed',
                        data: data,
                        backgroundColor: '#00d9ff',
                        borderColor: '#00b8d4',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#333' } },
                        x: { grid: { color: '#333' } }
                    },
                    plugins: {
                        legend: { labels: { color: '#eee' } }
                    }
                }
            });
        }
    }
}).mount('#app');
</script>
</body>
</html>
