import React, { useState } from 'react';
import { api } from '../services/api';

export default function EmailScreen({ onCodeSent }) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);

    const handleSendCode = async () => {
        if (!email || !email.includes('@')) {
            setMessage({ text: '올바른 이메일 주소를 입력하세요', type: 'error' });
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
                <div className="help-text">인증 코드가 발송됩니다</div>
            </div>
            <button onClick={handleSendCode} disabled={loading}>
                {loading ? '처리 중...' : '인증 코드 받기'}
            </button>
        </div>
    );
}
