# Interface Next.js. Construire depuis la racine du dépôt : docker build -f infra/web.Dockerfile .
FROM node:26-slim AS build
RUN npm install -g pnpm@10.28.0
WORKDIR /web
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web ./
# L'adresse de l'API est figée à la construction (réécritures /api/*) et relue à l'exécution (pages serveur).
ARG API_URL=http://api:8000
ENV API_URL=$API_URL NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:26-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 API_URL=http://api:8000
WORKDIR /web
RUN useradd --system --uid 10001 medai
COPY --from=build --chown=10001 /web/.next/standalone ./
COPY --from=build --chown=10001 /web/.next/static ./.next/static
USER 10001
EXPOSE 3000
CMD ["node", "server.js"]
