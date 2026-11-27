import { useState, type ComponentProps } from 'react';

export type AvatarProps = ComponentProps<'span'> & {
    name: string;
    src?: string;
    size?: 'sm' | 'md' | 'lg';
};

export function Avatar({
    name, src, size = 'md', className = '', ...props
}: AvatarProps) {
    const [failedSrc, setFailedSrc] = useState<string>();
    const initial = Array.from(name.trim())[0]?.toUpperCase() || '?';
    return <span role="img" aria-label={name} {...props}
        className={`ui-avatar ui-avatar--${size} ${className}`}>
        {src && src !== failedSrc
            ? <img src={src} alt=""
                onError={() => setFailedSrc(src)} />
            : initial}
    </span>;
}
