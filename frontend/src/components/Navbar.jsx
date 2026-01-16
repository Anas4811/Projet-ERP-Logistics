import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Chip,
} from '@mui/material';
import {
  AccountCircle,
  ExitToApp,
  Dashboard,
  Business,
  ShoppingCart,
  LocalShipping,
  Security,
  AdminPanelSettings,
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasRole } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
    handleClose();
  };

  const navigationItems = [
    { path: '/dashboard', label: 'Dashboard', icon: <Dashboard />, roles: ['admin', 'warehouse', 'operator', 'driver', 'vendor'] },
    { path: '/vendors', label: 'Vendors', icon: <Business />, roles: ['admin', 'warehouse', 'operator'] },
    { path: '/purchase-orders', label: 'Purchase Orders', icon: <ShoppingCart />, roles: ['admin', 'warehouse', 'operator'] },
    { path: '/asn', label: 'ASN & Tracking', icon: <LocalShipping />, roles: ['admin', 'warehouse', 'operator', 'driver'] },
    { path: '/gate', label: 'Gate Check-in', icon: <Security />, roles: ['admin', 'warehouse', 'operator', 'driver'] },
  ];

  const filteredNavItems = navigationItems.filter(item =>
    item.roles.some(role => hasRole(role))
  );

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, cursor: 'pointer' }} onClick={() => navigate('/dashboard')}>
          ERP Logistics System
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {filteredNavItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              sx={{
                backgroundColor: location.pathname === item.path ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                },
              }}
            >
              {item.label}
            </Button>
          ))}

          {hasRole('admin') && (
            <Button
              color="inherit"
              startIcon={<AdminPanelSettings />}
              onClick={() => navigate('/admin/users')}
              sx={{
                backgroundColor: location.pathname.startsWith('/admin') ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                },
              }}
            >
              Admin
            </Button>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {user?.roles?.map((role) => (
              <Chip
                key={role.id}
                label={role.name}
                size="small"
                color="secondary"
                variant="outlined"
              />
            ))}

            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              <Avatar sx={{ width: 32, height: 32 }}>
                {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
              </Avatar>
            </IconButton>

            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem disabled>
                <Typography variant="body2">
                  {user?.first_name} {user?.last_name}
                </Typography>
              </MenuItem>
              <MenuItem disabled>
                <Typography variant="body2" color="text.secondary">
                  {user?.email}
                </Typography>
              </MenuItem>
              <MenuItem onClick={handleClose}>
                <AccountCircle sx={{ mr: 1 }} />
                Profile
              </MenuItem>
              <MenuItem onClick={handleLogout}>
                <ExitToApp sx={{ mr: 1 }} />
                Logout
              </MenuItem>
            </Menu>
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
