FROM oven/bun:1

WORKDIR /app

# Copy package files
COPY package.json bun.lockb* ./

# Install dependencies
RUN bun install

# Copy application
COPY . .

EXPOSE 3001

CMD ["bun", "run", "dev"]
