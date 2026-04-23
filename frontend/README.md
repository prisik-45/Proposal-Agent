# Proposal Agent Frontend

A modern React + TypeScript + Tailwind CSS chatbot interface for the Proposal Agent API.

## Features

- 💬 **Chat Interface**: Natural language input for proposal generation
- 🎨 **Modern UI**: Built with Tailwind CSS and Vite
- ⚡ **Real-time Updates**: Displays extracted parameters and generation status
- 📥 **PDF Download**: Direct link to generated proposal on Google Drive
- 🔄 **API Integration**: Seamless integration with FastAPI backend

## Prerequisites

- Node.js 16+ or npm/yarn/pnpm

## Setup

### 1. Install Dependencies

```bash
npm install
# or
yarn install
# or
pnpm install
```

### 2. Run Development Server

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

The app will be available at `http://localhost:5173`

### 3. Build for Production

```bash
npm run build
# or
yarn build
# or
pnpm build
```

## Architecture

### Components

- **ChatInterface**: Main chat container with messages and input
- **Message**: Individual chat message bubble
- **ParametersDisplay**: Sidebar showing extracted parameters and results

### Types

- **ProposalResponse**: API response format
- **ExtractedParams**: Extracted proposal parameters from natural language
- **ProposalRequest**: Natural language input request

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`:

- **POST `/proposals/generate`**: Generate proposal from natural language input
- Returns: PDF link, extracted parameters, and success status

## Environment Configuration

The app is configured to proxy API requests through Vite:
- Frontend runs on `http://localhost:5173`
- API backend runs on `http://localhost:8000`
- Proxy configured in `vite.config.ts`

## Example Usage

1. Start the backend: `uv run python run_api.py`
2. Start the frontend: `npm run dev`
3. Open `http://localhost:5173` in your browser
4. Enter a proposal requirement in natural language
5. Click "Send" to generate the proposal
6. Download the PDF from the Google Drive link

## Deployment

### Vercel

```bash
npm install -g vercel
vercel
```

### Netlify

```bash
npm install -g netlify-cli
netlify deploy
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## Technologies

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Axios**: HTTP client
- **React DOM**: DOM rendering

## License

MIT
