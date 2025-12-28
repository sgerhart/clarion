# React Frontend - Production UI

## Overview

The Clarion frontend is now built with **React + TypeScript** for production use. It features:

- **White/Light Theme** - Clean, professional appearance
- **High Performance** - Optimized for large datasets (100K+ flows)
- **Modern Stack** - React 18, Vite, Tailwind CSS, React Query
- **Interactive Visualizations** - D3.js network graphs, Plotly.js heatmaps
- **Responsive Design** - Works on desktop and tablet

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | React 18 + TypeScript |
| **Build Tool** | Vite (fast HMR) |
| **Styling** | Tailwind CSS (white theme) |
| **Data Fetching** | React Query (caching, refetching) |
| **Routing** | React Router v6 |
| **Network Graphs** | D3.js |
| **Charts** | Plotly.js, Recharts |
| **Icons** | Lucide React |

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

Or use the setup script:
```bash
./scripts/setup_frontend.sh
```

### 2. Start Development Server

```bash
npm run dev
```

Frontend: `http://localhost:3000`  
Backend API: `http://localhost:8000` (must be running)

### 3. Build for Production

```bash
npm run build
```

Output: `frontend/dist/` (static files ready to serve)

## Pages

### 1. Dashboard (`/`)
- System overview metrics
- Total endpoints, flows, clusters, switches
- System health status

### 2. Network Flows (`/flows`)
- **Device-to-device flow visualization** (D3.js network graph)
- **Flow metadata table** (5/9-tuple: src_ip, dst_ip, ports, protocol, bytes, packets)
- Filters: protocol, source device, destination device
- Real-time flow data from database

### 3. Clusters (`/clusters`)
- **Cluster list** with SGT assignments
- **Device membership** - See which devices are in each cluster
- Device details: endpoint ID, switch, user, device name, AD groups
- Interactive cluster selection

### 4. SGT Matrix (`/matrix`)
- **Interactive heatmap** (Plotly.js) showing SGT × SGT communication
- Matrix details table with flows, bytes, top ports
- Build/refresh functionality
- Color-coded by flow volume

### 5. Policy Builder (`/policies`)
- Generate SGACL policies from matrix
- View and edit policy rules
- Export to Cisco CLI, ISE JSON, or JSON
- Policy customization interface

## API Integration

The frontend connects to the FastAPI backend via:

- **Base URL**: `http://localhost:8000/api`
- **Proxy**: Vite dev server proxies `/api/*` to backend
- **Authentication**: None (add as needed for production)

### API Endpoints Used

- `GET /api/health` - Health check
- `GET /api/edge/sketches` - List sketches
- `GET /api/edge/sketches/stats` - Sketch statistics
- `GET /api/netflow/netflow` - Get flow records
- `GET /api/clustering/clusters` - List clusters
- `GET /api/clustering/clusters/{id}/members` - Cluster members
- `POST /api/clustering/matrix/build` - Build SGT matrix
- `GET /api/clustering/matrix` - Get matrix
- `POST /api/policy/generate` - Generate policies
- `GET /api/policy/policies` - List policies

## Logo

Place your Clarion logo as:
- `frontend/public/clarion-logo.svg`

The logo appears in the header. A placeholder SVG is included.

## Performance

### Optimizations

1. **React Query** - Automatic caching, background refetching
2. **Virtual Scrolling** - For large flow tables (future enhancement)
3. **Lazy Loading** - Code splitting for routes
4. **Memoization** - Expensive calculations cached
5. **Pagination** - Large datasets paginated

### Handling Large Datasets

- Flow tables show first 100 rows (add pagination as needed)
- Network graph limited to 100 flows for performance
- Matrix heatmap handles 100+ SGTs efficiently
- React Query caches responses to reduce API calls

## Development

### Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable components
│   │   ├── Layout.tsx
│   │   ├── FlowGraph.tsx
│   │   └── FlowTable.tsx
│   ├── pages/          # Page components
│   │   ├── Dashboard.tsx
│   │   ├── NetworkFlows.tsx
│   │   ├── Clusters.tsx
│   │   ├── SGTMatrix.tsx
│   │   └── PolicyBuilder.tsx
│   ├── lib/            # Utilities
│   │   └── api.ts      # API client
│   ├── App.tsx         # Main app component
│   └── main.tsx        # Entry point
├── public/             # Static assets
│   └── clarion-logo.svg
├── package.json
└── vite.config.ts
```

### Adding New Features

1. **New Page**: Create in `src/pages/`, add route in `App.tsx`
2. **New Component**: Create in `src/components/`
3. **New API Endpoint**: Add to `src/lib/api.ts`
4. **Styling**: Use Tailwind classes (white theme)

## Production Deployment

### Build

```bash
npm run build
```

### Serve Static Files

Options:
1. **Nginx** - Serve `dist/` directory
2. **FastAPI Static Files** - Mount `dist/` in FastAPI
3. **CDN** - Upload to S3/CloudFront
4. **Docker** - Multi-stage build with nginx

### Environment Variables

Create `.env.production`:
```
VITE_API_URL=https://api.clarion.example.com
```

## Comparison: Streamlit vs React

| Feature | Streamlit | React |
|---------|-----------|-------|
| **Performance** | Slower for large data | Fast, optimized |
| **Customization** | Limited | Full control |
| **Real-time Updates** | Page refresh | WebSocket/SSE ready |
| **Network Visualizations** | Basic | D3.js, Cytoscape |
| **Production Ready** | Prototype | Yes |
| **Development Speed** | Fast | Moderate |
| **Bundle Size** | N/A | ~500KB (gzipped) |

## Next Steps

1. **Add Authentication** - JWT tokens, user sessions
2. **WebSocket Support** - Real-time flow updates
3. **Advanced Visualizations** - Cytoscape.js for better network graphs
4. **Virtual Scrolling** - Handle 1M+ flows efficiently
5. **Export Features** - Download flows, policies as CSV/JSON
6. **Search & Filter** - Advanced filtering UI
7. **Dark Mode Toggle** - Optional dark theme

## Troubleshooting

### Frontend won't start
- Check Node.js version: `node -v` (need 18+)
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### API calls failing
- Ensure backend is running: `python scripts/run_api.py`
- Check CORS settings in FastAPI
- Verify API URL in browser dev tools

### Build errors
- Check TypeScript errors: `npm run build`
- Fix linting: `npm run lint`

## Support

For issues or questions:
- Check browser console for errors
- Check backend logs
- Verify API endpoints in `/api/docs`


