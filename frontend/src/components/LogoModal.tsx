import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  ModalCloseButton,
} from "@chakra-ui/react";
import Image from "next/image";

interface LogoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LogoModal({ isOpen, onClose }: LogoModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="xl">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none">
        <ModalCloseButton color="white" />
        <ModalBody p={0}>
          <Image
            src="/icon.png"
            alt="SNEL Logo Large"
            width={400}
            height={400}
            priority
            style={{
              width: "100%",
              height: "auto",
              objectFit: "contain",
            }}
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
