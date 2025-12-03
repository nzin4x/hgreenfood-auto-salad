import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function EmailScreen({ onCodeSent }) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [regStatus, setRegStatus] = useState({ count: 0, limit: 10, isFull: false });

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const status = await api.getRegistrationStatus();
                setRegStatus(status);
            } catch (error) {
                console.error('Failed to fetch registration status:', error);
            }
        };
        fetchStatus();
    }, []);

    const handleSendCode = async () => {
        if (!email || !email.includes('@')) {
            setMessage({ text: '올바른 이메일 주소를 입력하세요', type: 'error' });
            return;
        }

        if (regStatus.isFull) {
            setMessage({
                text: `가입 한도 초과로 신규 가입이 불가합니다. (현재 ${regStatus.count}/${regStatus.limit}명)` ,
                type: 'error'
            });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            await api.sendVerificationCode(email);
            setMessage({ text: '인증 코드가 이메일로 발송되었습니다', type: 'success' });
            setTimeout(() => onCodeSent(email), 1000);
        } catch (error) {
            setMessage({ text: error.message, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div style={{ 
                marginBottom: '20px', 
                padding: '10px', 
                backgroundColor: regStatus.isFull ? '#ffebee' : '#e8f5e9',
                borderRadius: '4px',
                textAlign: 'center',
                color: regStatus.isFull ? '#c62828' : '#2e7d32',
                fontWeight: 'bold'
            }}>
                현재 가입자: {regStatus.count} / {regStatus.limit} 명
                {regStatus.isFull && <div>(가입 마감)</div>}
            </div>

            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}
            
            <div className="form-group">
                <label htmlFor="email">이메일 주소</label>
                <input 
                    type="email" 
                    id="email" 
                    placeholder="your@email.com" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required 
                />
                <div className="help-text">
                    {regStatus.isFull
                        ? '현재 신규 가입이 마감되어 인증 코드를 받을 수 없습니다.'
                        : '인증 코드가 발송됩니다'}
                </div>
            </div>
            <button onClick={handleSendCode} disabled={loading || regStatus.isFull}>
                {loading ? '처리 중...' : '인증 코드 받기'}
            </button>
        </div>
    );
}
