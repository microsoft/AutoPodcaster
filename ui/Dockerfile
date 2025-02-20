FROM node:18

WORKDIR /app

# Install dependencies first (better caching)
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Expose the port (adjust based on your dev server)
EXPOSE 5173

# Add --host flag to listen on all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]