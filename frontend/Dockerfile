FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
ARG VITE_GUARDBOX_API_URL
ENV VITE_GUARDBOX_API_URL=$VITE_GUARDBOX_API_URL
ARG VITE_TELEGRAM_BOT_ID
ENV VITE_TELEGRAM_BOT_ID=$VITE_TELEGRAM_BOT_ID
RUN npm run build

FROM nginx:alpine-slim
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
