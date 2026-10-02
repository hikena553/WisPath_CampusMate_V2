# syntax=docker/dockerfile:1
# 前端镜像：node:20 构建产物 → nginx:alpine 静态托管
# nginx 代理配置由 docker-compose 挂载（deploy/nginx.conf），不入镜像
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80