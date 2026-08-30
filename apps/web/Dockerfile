FROM node:22-bookworm-slim AS builder

WORKDIR /app
COPY package.json package-lock.json ./
COPY .npmrc .npmrc
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web

# 生产环境把 API 基址设为空（相对路径）
ENV VITE_API_BASE_URL=
RUN npm run build -w @maic/web

FROM nginx:1.25-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]