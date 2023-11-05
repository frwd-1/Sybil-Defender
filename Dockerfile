# Builder stage for Python dependencies
FROM python:3.9-alpine as python-builder
RUN apk update && apk add --virtual build-deps gcc python3-dev musl-dev postgresql-dev
RUN apk add libpq
RUN python3 -m pip install --upgrade pip
COPY requirements.txt ./
# Install Python dependencies globally to avoid .local copy
RUN pip install -r requirements.txt

# Builder stage for Node dependencies
FROM node:12-alpine as node-builder
WORKDIR /node_app
COPY package*.json ./
# Install production Node dependencies only
RUN npm ci --only=production

# Final stage: Set up the production environment
FROM python:3.9-alpine
# Install PostgreSQL client (if required by your bot)
RUN apk add --no-cache libpq
# Copy Python dependencies
COPY --from=python-builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
# Copy Node.js dependencies and application
COPY --from=node-builder /node_app/node_modules /app/node_modules
COPY --from=node-builder /node_app/package*.json /app/
COPY ./src /app/src
COPY LICENSE.md /app/

# Set up environment variables
ENV PATH=/usr/local/bin:$PATH
ENV NODE_ENV=production
# Uncomment the following line to enable agent logging
# LABEL "network.forta.settings.agent-logs.enable"="true"

WORKDIR /app
CMD [ "npm", "run", "start:prod" ]
