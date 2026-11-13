# syntax=docker/dockerfile:1
# The web server for hosting (compose.prod.yaml): the built app, served by Caddy, which also forwards /v1 to the API
# and gets HTTPS certificates by itself (infra/caddy/Caddyfile). Development uses the Vite server in compose.yaml.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2.10-alpine
COPY --from=build /app/dist /srv
