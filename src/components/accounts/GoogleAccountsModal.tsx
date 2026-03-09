import { createPortal } from 'react-dom';
import { useState, useEffect } from 'react';
import {
  authenticateGoogle,
  listGoogleAccounts,
  removeGoogleAccount,
  syncGoogleCalendar,
  TokenData,
  SyncResult,
} from '../../api';

interface GoogleAccountsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function GoogleAccountsModal({ isOpen, onClose }: GoogleAccountsModalProps) {
  const [accounts, setAccounts] = useState<TokenData[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncResults, setSyncResults] = useState<Record<string, SyncResult>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadAccounts();
    }
  }, [isOpen]);

  const loadAccounts = async () => {
    try {
      setError(null);
      const accts = await listGoogleAccounts();
      setAccounts(accts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts');
    }
  };

  const handleAddAccount = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await authenticateGoogle();
      setAccounts([...accounts, token]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveAccount = async (email: string | null) => {
    if (!email) return;
    try {
      await removeGoogleAccount(email);
      setAccounts(accounts.filter((a) => a.account_email !== email));
      setSyncResults((prev) => {
        const newResults = { ...prev };
        delete newResults[email];
        return newResults;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove account');
    }
  };

  const handleSync = async (email: string | null) => {
    if (!email) return;
    setSyncing(email);
    setError(null);
    try {
      const result = await syncGoogleCalendar(email, 'primary');
      setSyncResults((prev) => ({ ...prev, [email]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed');
    } finally {
      setSyncing(null);
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel google-accounts-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <p className="modal-title">Google Calendar Accounts</p>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-content">
          {error && (
            <div className="error-banner">
              <p className="error-text">{error}</p>
            </div>
          )}

          {accounts.length === 0 ? (
            <div className="empty-state">
              <p>No Google accounts connected yet</p>
            </div>
          ) : (
            <div className="accounts-list">
              {accounts.map((account) => (
                <div key={account.account_email} className="account-item">
                  <div className="account-info">
                    <p className="account-email">{account.account_email || 'Unknown'}</p>
                    {syncResults[account.account_email || ''] && (
                      <p className="sync-status">
                        Synced: {syncResults[account.account_email || ''].created} created,{' '}
                        {syncResults[account.account_email || ''].updated} updated
                      </p>
                    )}
                  </div>
                  <div className="account-actions">
                    <button
                      className="btn btn--sm btn--primary"
                      onClick={() => handleSync(account.account_email)}
                      disabled={syncing === account.account_email}
                    >
                      {syncing === account.account_email ? 'Syncing...' : 'Sync Now'}
                    </button>
                    <button
                      className="btn btn--sm btn--danger"
                      onClick={() => handleRemoveAccount(account.account_email)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn btn--primary"
            onClick={handleAddAccount}
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Add Google Account'}
          </button>
          <button className="btn btn--secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
