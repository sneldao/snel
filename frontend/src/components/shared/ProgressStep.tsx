import * as React from "react";
import {
  HStack,
  VStack,
  Text,
  Progress,
} from "@chakra-ui/react";
import { CheckCircleIcon } from "@chakra-ui/icons";

interface ProgressStepProps {
  step: string;
  icon: string;
  delay: number;
  isActive: boolean;
}

export const ProgressStep: React.FC<ProgressStepProps> = ({ 
  step, 
  icon, 
  delay, 
  isActive 
}) => {
  const [isVisible, setIsVisible] = React.useState(false);
  const [progress, setProgress] = React.useState(0);

  React.useEffect(() => {
    if (isActive) {
      const timer = setTimeout(() => {
        setIsVisible(true);
        // Animate progress
        let currentProgress = 0;
        const progressInterval = setInterval(() => {
          currentProgress += 5;
          setProgress(currentProgress);
          if (currentProgress >= 100) {
            clearInterval(progressInterval);
          }
        }, 100);
      }, delay);

      return () => clearTimeout(timer);
    }
  }, [isActive, delay]);

  if (!isVisible) {
    return (
      <HStack spacing={3} opacity={0.3}>
        <Text fontSize="md">{icon}</Text>
        <Text fontSize="sm" color="whiteAlpha.600">
          {step}
        </Text>
      </HStack>
    );
  }

  return (
    <VStack spacing={2} align="stretch">
      <HStack spacing={3}>
        <Text fontSize="md">{icon}</Text>
        <VStack align="start" spacing={1} flex={1}>
          <Text fontSize="sm" fontWeight="medium" color="whiteAlpha.900">
            {step}
          </Text>
          <Progress
            value={progress}
            size="xs"
            colorScheme="blue"
            borderRadius="full"
            bg="whiteAlpha.200"
            hasStripe
            isAnimated={progress < 100}
            w="100%"
          />
        </VStack>
        {progress === 100 && <CheckCircleIcon color="green.400" boxSize={3} />}
      </HStack>
    </VStack>
  );
};
