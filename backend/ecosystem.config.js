module.exports = {
  apps: [
    {
      name: 'snel-backend',
      script: './start.sh',
      cwd: '/root/snel/backend',
      interpreter: '/bin/bash',
      
      // Execution mode
      instances: 1,
      exec_mode: 'fork',
      
      // Restart policies
      max_memory_restart: '500M',
      watch: false, // Don't watch files in production
      
      // Environment variables
      env: {
        NODE_ENV: 'production',
      },
      
      // Logging
      output: '/root/snel/backend/logs/out.log',
      error: '/root/snel/backend/logs/error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      
      // Startup and shutdown behavior
      wait_ready: true,
      listen_timeout: 10000,
      kill_timeout: 5000,
      
      // Monitoring
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
    }
  ]
};
