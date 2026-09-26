FROM node:20-alpine AS base
WORKDIR /app

# NEXT_PUBLIC_* are baked in at build time — override with --build-arg.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws
ARG NEXT_PUBLIC_APP_NAME="Shared Inbox"
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./
RUN npm run build

EXPOSE 3000
ENV NODE_ENV=production
CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
