# Multi-stage build for production

# Stage 1: Development
FROM node:18-alpine as development

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]

# Stage 2: Build
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Accept API URL as build argument
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Accept Google Client ID as build argument
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

RUN npm run build

# Stage 3: Production with nginx
FROM nginx:alpine as production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check for nginx
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost/ || exit 1

CMD ["/bin/sh", "-c", "sed -i \"s/PORT_PLACEHOLDER/${PORT:-80}/g\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
