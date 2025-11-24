import React, { useState } from 'react';
import { api } from '../services/api';

export default function VerifyScreen({ email, deviceFingerprint, onVerified, onBack }) {
    const [code, setCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);

    const handleVerify = async () => {
        if (code.length !== 6) {
            setMessage({ text: '6자리 인증 코드를 입력하세요', type: 'error' });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const data = await api.verifyCode(email, code, deviceFingerprint);
            onVerified(data);
        } catch (error) {
            setMessage({ text: error.message, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}

            <div className="form-group">
                <label htmlFor="verificationCode">인증 코드</label>
                <input 
                    type="text" 
                    id="verificationCode" 
                    placeholder="6자리 숫자" 
                    maxLength="6" 
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    required 
                />
                <div className="help-text">이메일로 받은 6자리 코드를 입력하세요</div>
            </div>
            <button onClick={handleVerify} disabled={loading}>
                {loading ? '처리 중...' : '인증 확인'}
            </button>
            <button onClick={onBack} style={{ marginTop: '10px', background: '#6c757d' }}>
                다시 입력
            </button>
        </div>
    );
}
