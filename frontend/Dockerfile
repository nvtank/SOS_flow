FROM node:22-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Vite variables are compiled into the static bundle.  Compose supplies these
# build arguments for the regular and one-day-demo endpoints.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_DEMO_MODE=false
ARG VITE_DEMO_TOKEN=sosflow-demo
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_DEMO_MODE=$VITE_DEMO_MODE
ENV VITE_DEMO_TOKEN=$VITE_DEMO_TOKEN
RUN npm run build

# Preview is only the local container host for the already-static dist/ output.
# Production publishes the same dist/ directory through S3 + CloudFront.
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
