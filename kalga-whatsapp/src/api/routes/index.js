/**
 * Agrégation de toutes les routes API
 */
const express = require('express');
const connectRoutes = require('./connect.routes');
const sendRoutes = require('./send.routes');
const statusRoutes = require('./status.routes');

const router = express.Router();

// Monter les routes
router.use('/', connectRoutes);
router.use('/', sendRoutes);
router.use('/', statusRoutes);

module.exports = router;
