import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import ExclusionCalendar from './ExclusionCalendar';

export default function SettingsModal({ user, onClose, onSaved }) {
    const [menuSeq, setMenuSeq] = useState('샐,샌,빵');
    const [floorNm, setFloorNm] = useState('5층');
    const [hgUserId, setHgUserId] = useState('');
    const [hgUserPw, setHgUserPw] = useState('');
    const [exclusionDates, setExclusionDates] = useState([]);
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadSettings = async () => {
            try {
                const settings = await api.getUserSettings(user.userId);
                if (settings.menuSeq && settings.menuSeq.length > 0) {
                    setMenuSeq(settings.menuSeq.join(','));
                }
                if (settings.floorNm) {
                    setFloorNm(settings.floorNm);
                }
                if (settings.exclusionDates) {
                    setExclusionDates(settings.exclusionDates);
                }
                // Note: We don't load password for security
            } catch (err) {
                console.error('Failed to load settings:', err);
                // 기본값 유지
            } finally {
                setLoading(false);
            }
        };
        loadSettings();
    }, [user.userId]);

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const menuArray = menuSeq.split(',').map(m => m.trim()).filter(m => m);
            await api.updateUserSettings(
                user.userId, 
                menuArray, 
                floorNm || undefined,
                hgUserId || undefined,
                hgUserPw || undefined
            );
            onSaved();
        } catch (err) {
            console.error('Settings update error:', err);
            setError(err.message || '설정 저장 실패');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveExclusionDates = async (dates) => {
        try {
            await api.updateExclusionDates(user.userId, dates);
            setExclusionDates(dates);
            alert('제외 날짜가 저장되었습니다');
        } catch (err) {
            console.error('Exclusion dates update error:', err);
            alert(err.message || '제외 날짜 저장 실패');
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
                maxHeight: '90vh',
                overflowY: 'auto',
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
                        placeholder="예: 샌,샐,빵"
                        style={{
                            width: '100%',
                            padding: '12px',
                            border: '2px solid #e0e0e0',
                            borderRadius: '8px',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                    <div style={{ 
                        marginTop: '8px', 
                        padding: '10px', 
                        background: '#f5f5f5', 
                        borderRadius: '6px',
                        fontSize: '12px',
                        color: '#666'
                    }}>
                        <div style={{ fontWeight: 600, marginBottom: '5px' }}>메뉴 코드:</div>
                        <div>• 샌 = 샌드위치 (0005)</div>
                        <div>• 샐 = 샐러드 (0006)</div>
                        <div>• 빵 = 베이커리 (0007)</div>
                        <div>• 헬 = 헬시세트 (0009)</div>
                        <div>• 닭 = 닭가슴살 (0010)</div>
                        <div style={{ marginTop: '5px', fontStyle: 'italic' }}>쉼표(,)로 구분하세요</div>
                    </div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: '#333' }}>
                        n층
                    </label>
                    <input
                        type="text"
                        value={floorNm}
                        onChange={(e) => setFloorNm(e.target.value)}
                        placeholder="5층"
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

                <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: '#333' }}>
                        HGreen ID (선택사항)
                    </label>
                    <input
                        type="text"
                        value={hgUserId}
                        onChange={(e) => setHgUserId(e.target.value)}
                        placeholder="변경할 경우에만 입력"
                        style={{
                            width: '100%',
                            padding: '12px',
                            border: '2px solid #e0e0e0',
                            borderRadius: '8px',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                    <small style={{ color: '#999', fontSize: '11px' }}>
                        비워두면 변경되지 않습니다
                    </small>
                </div>

                <div style={{ marginBottom: '25px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: '#333' }}>
                        HGreen 비밀번호 (선택사항)
                    </label>
                    <input
                        type="password"
                        value={hgUserPw}
                        onChange={(e) => setHgUserPw(e.target.value)}
                        placeholder="변경할 경우에만 입력"
                        style={{
                            width: '100%',
                            padding: '12px',
                            border: '2px solid #e0e0e0',
                            borderRadius: '8px',
                            fontSize: '14px',
                            boxSizing: 'border-box'
                        }}
                    />
                    <small style={{ color: '#999', fontSize: '11px' }}>
                        비워두면 변경되지 않습니다
                    </small>
                </div>

                {/* Exclusion Calendar */}
                <div style={{ marginBottom: '25px' }}>
                    <ExclusionCalendar 
                        userId={user.userId}
                        initialDates={exclusionDates}
                        onSave={handleSaveExclusionDates}
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
                        disabled={saving || loading}
                        style={{
                            padding: '12px 24px',
                            background: '#667eea',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: (saving || loading) ? 'not-allowed' : 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                            opacity: (saving || loading) ? 0.6 : 1
                        }}
                    >
                        {saving ? '저장 중...' : loading ? '로딩 중...' : '저장'}
                    </button>
                </div>
            </div>
        </div>
    );
}
