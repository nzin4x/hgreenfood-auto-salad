import React, { useState } from 'react';
import { api } from '../services/api';

export default function SettingsModal({ user, onClose, onSaved }) {
    const [menuSeq, setMenuSeq] = useState('백반A,백반B,백반C');
    const [floorNm, setFloorNm] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const menuArray = menuSeq.split(',').map(m => m.trim()).filter(m => m);
            await api.updateUserSettings(user.userId, menuArray, floorNm || undefined);
            onSaved();
        } catch (err) {
            console.error('Settings update error:', err);
            setError(err.message || '설정 저장 실패');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
        }}>
            <div style={{
                background: 'white',
                borderRadius: '12px',
                padding: '30px',
                maxWidth: '500px',
                width: '90%',
                boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
            }}>
                <h2 style={{ marginTop: 0, marginBottom: '20px', color: '#667eea' }}>설정</h2>
                
                {error && (
                    <div className="message error" style={{ marginBottom: '15px' }}>
                        {error}
                    </div>
                )}

                <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: '#333' }}>
                        메뉴 선호 순서
                    </label>
                    <input
                        type="text"
                        value={menuSeq}
                        onChange={(e) => setMenuSeq(e.target.value)}
                        placeholder="예: 백반A,백반B,백반C"
                        style={{
                            width: '100%',
                            padding: '12px',
                            border: '2px solid #e0e0e0',
                            borderRadius: '8px',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                    <small style={{ color: '#666', fontSize: '12px' }}>
                        쉼표(,)로 구분하여 입력하세요
                    </small>
                </div>

                <div style={{ marginBottom: '25px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: '#333' }}>
                        층 (선택사항)
                    </label>
                    <input
                        type="text"
                        value={floorNm}
                        onChange={(e) => setFloorNm(e.target.value)}
                        placeholder="예: 본관1층"
                        style={{
                            width: '100%',
                            padding: '12px',
                            border: '2px solid #e0e0e0',
                            borderRadius: '8px',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                </div>

                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                    <button
                        onClick={onClose}
                        disabled={saving}
                        style={{
                            padding: '12px 24px',
                            background: '#6c757d',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: saving ? 'not-allowed' : 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                            opacity: saving ? 0.6 : 1
                        }}
                    >
                        취소
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        style={{
                            padding: '12px 24px',
                            background: '#667eea',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: saving ? 'not-allowed' : 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                            opacity: saving ? 0.6 : 1
                        }}
                    >
                        {saving ? '저장 중...' : '저장'}
                    </button>
                </div>
            </div>
        </div>
    );
}
