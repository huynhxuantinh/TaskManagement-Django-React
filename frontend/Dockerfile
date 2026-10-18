FROM node:24.14.1-alpine3.23

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN chown -R node:node /app

USER node

EXPOSE 5173

CMD ["npm", "run", "dev"]
