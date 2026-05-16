FROM node:22-alpine

WORKDIR /app

# Install deps first for better layer caching. We don't ship a lockfile yet —
# `npm install` (not `ci`) lets the image build before the first commit.
COPY package.json ./
RUN npm install

# Source is bind-mounted in docker-compose for hot reload, so we don't need to
# COPY the rest. Keeping the layer small.

EXPOSE 3000

# WATCHPACK_POLLING helps file change detection on Docker Desktop / Windows.
ENV WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_TELEMETRY_DISABLED=1

CMD ["npm", "run", "dev"]
