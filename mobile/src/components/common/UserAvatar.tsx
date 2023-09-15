import { IonAvatar, IonSkeletonText } from '@ionic/react'
import avatar from '@/assets/male-avatar.svg'
import { StyleReactProps } from '@ionic/react/dist/types/components/react-component-lib/interfaces'
import { useInView } from 'react-intersection-observer';

interface AvatarProps {
    src?: string,
    alt: string,
    slot?: string,
    isActive?: boolean,
    className?: StyleReactProps['className']
}
const options = {
    root: null,
    rootMargin: "50px",
    threshold: 0.5,
    triggerOnce: true
};
export const UserAvatar = ({ src, alt, slot, className, isActive }: AvatarProps) => {
    const { ref, inView } = useInView(options);
    return <span ref={ref} slot={slot} className="relative inline-block">
        {inView ? <img
            className="h-8 w-8 rounded-md bg-[color:var(--ion-color-light)] object-cover"
            src={src ? src : avatar}
            alt={alt}
            loading='lazy'
        /> : <IonSkeletonText animated className='w-8 h-8 rounded-md' />}
        {isActive &&
            <span className="absolute bottom-0 right-0 block translate-x-1/2 translate-y-1/2 transform rounded-full">
                <span className="block h-2 w-2 rounded-full bg-green-500" />
            </span>
        }
    </span>
}
export const SquareAvatar = ({ src, alt, className, isActive }: AvatarProps) => {
    const { ref, inView } = useInView(options);
    return <span ref={ref} className="relative inline-block">
        {inView ? <img
            className="h-8 w-8 rounded-md bg-[color:var(--ion-color-light)] object-cover"
            src={src ? src : avatar}
            alt={alt}
            loading='lazy'
        /> : <IonSkeletonText animated className='w-8 h-8 rounded-md' />}
        {isActive &&
            <span className="absolute bottom-0 right-0 block translate-x-1/2 translate-y-1/2 transform rounded-full">
                <span className="block h-2 w-2 rounded-full bg-green-500" />
            </span>
        }
    </span>
}