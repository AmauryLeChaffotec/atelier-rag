FROM node:22-alpine AS construction
WORKDIR /projet
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build
FROM node:22-alpine AS execution
WORKDIR /projet
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=construction --chown=node:node /projet/.next/standalone ./
COPY --from=construction --chown=node:node /projet/.next/static ./.next/static
COPY --from=construction --chown=node:node /projet/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
