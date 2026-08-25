FROM node:22-bookworm-slim AS builder

WORKDIR /app
COPY package.json package-lock.json ./
COPY .npmrc .npmrc
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/content/package.json packages/content/package.json
COPY packages/types/package.json packages/types/package.json
COPY packages/utils/package.json packages/utils/package.json
COPY packages/validation/package.json packages/validation/package.json
RUN npm ci
COPY apps/web apps/web
COPY packages packages

# 生产环境把 API 基址设为空（相对路径）
ENV VITE_API_BASE_URL=
RUN npm run build -w @maic/web

FROM nginx:1.25-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]