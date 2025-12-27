# Clarion Frontend

Production-ready React frontend for Clarion TrustSec Policy Copilot.

## Features

- **React + TypeScript** - Modern, type-safe frontend
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS with white theme
- **React Query** - Efficient data fetching and caching
- **D3.js** - Network flow visualizations
- **Plotly.js** - Interactive charts and heatmaps
- **React Router** - Client-side routing

## Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000` and proxy API requests to `http://localhost:8000`.

## Build for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

## Pages

- **Dashboard** (`/`) - System overview and metrics
- **Network Flows** (`/flows`) - Device-to-device flows with graph visualization
- **Clusters** (`/clusters`) - Cluster membership and device details
- **SGT Matrix** (`/matrix`) - SGT communication matrix heatmap
- **Policy Builder** (`/policies`) - SGACL policy generation and editing

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000/api`. All API calls are defined in `src/lib/api.ts`.

## Logo

Place the Clarion logo as `public/clarion-logo.svg` for it to appear in the header.


