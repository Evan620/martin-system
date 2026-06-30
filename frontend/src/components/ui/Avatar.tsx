import { HTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
    src?: string
    alt?: string
    size?: 'xs' | 'sm' | 'md' | 'lg'
    fallback?: string
}

export default function Avatar({
    src,
    alt = 'Avatar',
    size = 'md',
    fallback,
    className,
    ...props
}: AvatarProps) {
    const sizes = {
        xs: 'w-6 h-6 text-[8px]',
        sm: 'w-8 h-8 text-xs',
        md: 'w-10 h-10 text-sm',
        lg: 'w-12 h-12 text-base',
    }

    const initials = fallback || alt.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

    return (
        <div
            className={clsx(
                'rounded-full overflow-hidden bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center text-white font-semibold',
                sizes[size],
                className
            )}
            {...props}
        >
            {src ? (
                <img src={src} alt={alt} className="w-full h-full object-cover" />
            ) : (
                <span>{initials}</span>
            )}
        </div>
    )
}
