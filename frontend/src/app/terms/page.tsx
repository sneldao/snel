"use client";

import { Box, Container, Heading, Text, VStack, Link } from "@chakra-ui/react";
import { Footer } from "../../components/Footer";

export default function TermsAndConditions() {
  return (
    <>
      <Container maxW="container.lg" py={8} mb={16}>
        <VStack spacing={6} align="stretch">
          <Heading as="h1" size="xl" mb={4}>
            Terms and Conditions for Snel
          </Heading>
          <Text color="gray.500" fontWeight="medium">
            Last Updated: February 26, 2025
          </Text>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              1. Acceptance of Terms
            </Heading>
            <Text mb={4}>
              By accessing or using Snel, an artificial intelligence agent that
              facilitates cryptocurrency swaps and interacts with other agents
              to accomplish tasks (the "Service"), you agree to be bound by
              these Terms and Conditions (the "Terms"). If you do not agree to
              these Terms, you must not access or use the Service.
            </Text>
            <Text mb={4}>
              These Terms constitute a legally binding agreement between you and
              the developers of Snel ("we," "us," or "our"). You acknowledge
              that you have read, understood, and agree to be bound by these
              Terms, which may be updated by us from time to time without notice
              to you.
            </Text>
            <Text mb={4} fontWeight="bold">
              IMPORTANT NOTICE: BY USING SNEL, YOU EXPRESSLY ACKNOWLEDGE AND
              AGREE THAT YOU ARE ENTERING INTO A BINDING CONTRACT AND THAT YOUR
              USE OF THE SERVICE IS AT YOUR SOLE RISK.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              2. Service Description
            </Heading>
            <Text mb={4}>Snel is an AI agent designed to:</Text>
            <Text as="ul" pl={6} mb={4}>
              <Text as="li">
                Facilitate cryptocurrency swaps and transactions
              </Text>
              <Text as="li">
                Interact with other AI agents and smart contracts
              </Text>
              <Text as="li">
                Execute tasks on behalf of users based on provided instructions
              </Text>
              <Text as="li">Analyze on-chain data and smart contracts</Text>
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              3. Eligibility and Registration
            </Heading>
            <Text mb={4}>
              You must be at least 18 years old and capable of forming a legally
              binding contract to use our Service. By using Snel, you represent
              and warrant that you meet these eligibility requirements.
            </Text>
            <Text mb={4}>
              We reserve the right to request verification of your identity at
              any time and to suspend or terminate your access to the Service if
              we believe you do not meet our eligibility requirements or have
              violated these Terms.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              4. User Conduct and Prohibited Activities
            </Heading>
            <Text mb={4}>You agree not to use Snel to:</Text>
            <Text as="ul" pl={6} mb={4}>
              <Text as="li">
                Violate any applicable law, regulation, or third-party rights
              </Text>
              <Text as="li">
                Engage in market manipulation, front-running, or other forms of
                market abuse
              </Text>
              <Text as="li">
                Attempt to exploit vulnerabilities in blockchain protocols or
                smart contracts
              </Text>
              <Text as="li">
                Conduct transactions involving illegal goods or services
              </Text>
              <Text as="li">
                Engage in money laundering, terrorist financing, or other
                financial crimes
              </Text>
              <Text as="li">
                Circumvent any limitations or restrictions we place on the
                Service
              </Text>
              <Text as="li">
                Reverse engineer or attempt to extract the source code of Snel
              </Text>
              <Text as="li">
                Use Snel in connection with any high-risk activities where
                failure could lead to injury, death, or severe property damage
              </Text>
              <Text as="li">
                Attempt prompt injection or other attacks on Snel's underlying
                models
              </Text>
              <Text as="li">
                Use Snel to interact with blacklisted or sanctioned addresses or
                entities
              </Text>
            </Text>
            <Text mb={4}>
              We reserve the right to monitor your use of Snel to ensure
              compliance with these Terms.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              5. Disclaimer of Warranties
            </Heading>
            <Text mb={4} textTransform="uppercase">
              The service is provided "as is" and "as available," without
              warranty of any kind, express or implied. To the maximum extent
              permitted by applicable law, we explicitly disclaim all
              warranties, including any warranty of merchantability, fitness for
              a particular purpose, non-infringement, accuracy, completeness, or
              reliability.
            </Text>
            <Text mb={4} textTransform="uppercase">
              We do not warrant that:
            </Text>
            <Text as="ul" pl={6} mb={4} textTransform="uppercase">
              <Text as="li">
                Snel will function uninterrupted, securely, or be available at
                any particular time or place
              </Text>
              <Text as="li">Any errors or defects will be corrected</Text>
              <Text as="li">
                Snel is free of viruses or other harmful components
              </Text>
              <Text as="li">
                Snel will correctly interpret smart contracts or blockchain data
              </Text>
              <Text as="li">
                Results obtained from using Snel will be accurate, reliable, or
                meet your requirements
              </Text>
              <Text as="li">
                Snel will successfully complete any transaction or task
              </Text>
              <Text as="li">
                Snel will properly interact with other agents or services
              </Text>
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              6. Risk Disclosures and Assumption of Risk
            </Heading>
            <Text mb={4}>
              By using Snel, you expressly acknowledge and assume the following
              risks:
            </Text>

            <Heading as="h3" size="md" mb={2}>
              6.1 Technology Risks
            </Heading>
            <Text as="ul" pl={6} mb={4}>
              <Text as="li">Smart contract vulnerabilities</Text>
              <Text as="li">Blockchain network congestion or failure</Text>
              <Text as="li">Front-running or sandwich attacks</Text>
              <Text as="li">
                Incorrect parsing or interpretation of smart contract code
              </Text>
              <Text as="li">Failures in the AI systems powering Snel</Text>
              <Text as="li">Prompt injection or model manipulation</Text>
              <Text as="li">
                Exploits targeting Snel or services it interacts with
              </Text>
              <Text as="li">Software bugs or errors</Text>
              <Text as="li">Network connectivity issues</Text>
              <Text as="li">
                Malicious third-party applications or contracts
              </Text>
            </Text>

            <Heading as="h3" size="md" mb={2}>
              6.2 Financial Risks
            </Heading>
            <Text as="ul" pl={6} mb={4}>
              <Text as="li">Extreme price volatility in cryptocurrencies</Text>
              <Text as="li">
                Permanent loss of funds due to irreversible transactions
              </Text>
              <Text as="li">Impermanent loss from providing liquidity</Text>
              <Text as="li">
                High transaction fees during network congestion
              </Text>
              <Text as="li">
                Counterparty risks when interacting with other protocols
              </Text>
              <Text as="li">Slippage during swaps or trades</Text>
              <Text as="li">
                Gas price fluctuations affecting transaction costs
              </Text>
              <Text as="li">
                Failed transactions resulting in lost gas fees
              </Text>
              <Text as="li">Scams, frauds, or phishing attempts</Text>
              <Text as="li">
                Smart contract exploits resulting in drained funds
              </Text>
            </Text>

            <Heading as="h3" size="md" mb={2}>
              6.3 Risk Assumption
            </Heading>
            <Text mb={4} textTransform="uppercase">
              You expressly agree that you use Snel at your sole risk. You
              understand the inherent risks of cryptocurrency transactions and
              blockchain technology and accept full responsibility for any loss
              of value or damage you may experience. You acknowledge that Snel
              may misinterpret or incorrectly identify smart contract functions,
              which could result in unintended actions and potential loss of
              funds.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              7. Limitation of Liability
            </Heading>
            <Text mb={4} textTransform="uppercase">
              To the maximum extent permitted by applicable law, in no event
              shall we, our affiliates, employees, agents, or licensors be
              liable for any indirect, punitive, incidental, special,
              consequential, or exemplary damages, including damages for loss of
              profits, goodwill, use, data, or other intangible losses, arising
              out of or relating to your use of the service.
            </Text>
            <Text mb={4} textTransform="uppercase">
              Our total liability to you for all claims arising from or relating
              to these terms or your use of Snel, whether in contract, tort
              (including negligence), or otherwise, shall not exceed the lesser
              of: (a) the amount you paid to use Snel during the three (3)
              months immediately preceding the date on which the claim arose, or
              (b) $100 USD.
            </Text>
            <Text mb={4} textTransform="uppercase">
              These limitations apply even if we have been advised of the
              possibility of such damages and even if a remedy fails of its
              essential purpose.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              8. Indemnification
            </Heading>
            <Text mb={4}>
              You agree to defend, indemnify, and hold harmless us, our
              affiliates, licensors, and service providers, and our and their
              respective officers, directors, employees, contractors, agents,
              licensors, suppliers, successors, and assigns from and against any
              claims, liabilities, damages, judgments, awards, losses, costs,
              expenses, or fees (including reasonable attorneys' fees) arising
              out of or relating to your violation of these Terms or your use of
              Snel, including, but not limited to, any use of the Service's
              content, services, and products other than as expressly authorized
              in these Terms.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              9. Monitoring and Suspension Rights
            </Heading>
            <Text mb={4}>We reserve the right to:</Text>
            <Text as="ul" pl={6} mb={4}>
              <Text as="li">
                Monitor your use of Snel for compliance with these Terms
              </Text>
              <Text as="li">
                Suspend or terminate your access to Snel at any time, with or
                without notice, for any reason, including if we believe you have
                violated these Terms
              </Text>
              <Text as="li">
                Implement kill switches or other emergency measures to suspend
                or terminate Snel's operations if we determine, in our sole
                discretion, that Snel is operating in an unintended manner or
                poses a risk to users
              </Text>
              <Text as="li">
                Limit the functionality of Snel or restrict its operations to
                certain environments, blockchains, or contracts
              </Text>
            </Text>
            <Text mb={4} textTransform="uppercase">
              You acknowledge that we may suspend or terminate the service
              without notice and that we shall not be liable for any loss or
              damage resulting from such suspension or termination.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              10. User Confirmations and Approvals
            </Heading>

            <Heading as="h3" size="md" mb={2}>
              10.1 Transaction Approval
            </Heading>
            <Text mb={4}>
              Snel may present transactions for your review and approval before
              execution. You are solely responsible for reviewing and
              understanding any transaction before approving it. By approving a
              transaction, you acknowledge that you understand its nature,
              risks, and potential outcomes.
            </Text>

            <Heading as="h3" size="md" mb={2}>
              10.2 Implicit Approvals
            </Heading>
            <Text mb={4}>
              You acknowledge that by instructing Snel to perform certain tasks,
              you may be implicitly approving transactions or interactions with
              third-party services. You remain solely responsible for all
              consequences of such instructions, even if Snel executes them in a
              manner you did not anticipate.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              11. Non-Custodial Service
            </Heading>
            <Text mb={4}>
              Snel operates as a non-custodial service, meaning we do not take
              custody of your cryptocurrency assets at any time. You maintain
              sole control over your private keys and funds. Any transactions
              facilitated by Snel require your explicit consent or are executed
              through your own wallet.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              12. Third-Party Services and Agents
            </Heading>

            <Heading as="h3" size="md" mb={2}>
              12.1 Third-Party Interactions
            </Heading>
            <Text mb={4}>
              Snel may interact with third-party services, protocols, or other
              AI agents to fulfill your requests. We do not control these third
              parties and assume no responsibility for their actions, services,
              or content. Your use of any third-party service is subject to that
              third party's terms and privacy policies.
            </Text>

            <Heading as="h3" size="md" mb={2}>
              12.2 No Endorsement
            </Heading>
            <Text mb={4}>
              Our facilitation of interactions with third-party services does
              not constitute an endorsement, recommendation, or approval of such
              services. We make no representations regarding the quality,
              security, or legality of third-party services.
            </Text>

            <Heading as="h3" size="md" mb={2}>
              12.3 Agent-to-Agent Interactions
            </Heading>
            <Text mb={4}>
              When Snel interacts with other AI agents, you acknowledge that
              those interactions may involve additional risks, including:
            </Text>
            <Text as="ul" pl={6} mb={4}>
              <Text as="li">
                Misinterpretation of instructions or data between agents
              </Text>
              <Text as="li">Propagation of errors across multiple systems</Text>
              <Text as="li">
                Unpredictable behavior from agent-to-agent communication
              </Text>
              <Text as="li">
                Potential lack of transparency in complex agent interactions
              </Text>
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              13. Intellectual Property Rights
            </Heading>
            <Text mb={4}>
              All rights, title, and interest in and to Snel, including all
              intellectual property rights therein, are and will remain our
              exclusive property. Nothing in these Terms shall be construed as
              granting you a right to use any of our intellectual property.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              14. Modifications to Terms
            </Heading>
            <Text mb={4}>
              We reserve the right to modify these Terms at any time. All
              changes are effective immediately when posted. Your continued use
              of Snel following the posting of revised Terms means you accept
              and agree to the changes.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              15. Governing Law and Dispute Resolution
            </Heading>

            <Heading as="h3" size="md" mb={2}>
              15.1 Governing Law
            </Heading>
            <Text mb={4}>
              These Terms and your use of Snel shall be governed by and
              construed in accordance with the laws of the United States,
              without giving effect to any choice or conflict of law provision
              or rule.
            </Text>

            <Heading as="h3" size="md" mb={2}>
              15.2 Arbitration Agreement
            </Heading>
            <Text mb={4} textTransform="uppercase">
              Any dispute, claim, or controversy arising out of or relating to
              these terms or the service shall be resolved by binding
              arbitration administered by the American Arbitration Association
              in accordance with its commercial arbitration rules. The
              arbitration shall be conducted by one arbitrator selected in
              accordance with such rules. The arbitration shall be conducted in
              San Francisco, California. Judgment on the award rendered by the
              arbitrator may be entered in any court having jurisdiction
              thereof.
            </Text>
            <Text mb={4} textTransform="uppercase">
              You acknowledge that by agreeing to this arbitration provision,
              you waive the right to resolve disputes through a court or jury
              trial.
            </Text>

            <Heading as="h3" size="md" mb={2}>
              15.3 Class Action Waiver
            </Heading>
            <Text mb={4} textTransform="uppercase">
              You agree that any claims relating to these terms or the service
              shall be brought in your individual capacity, and not as a
              plaintiff or class member in any purported class or representative
              proceeding.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              16. Severability
            </Heading>
            <Text mb={4}>
              If any provision of these Terms is held to be invalid, illegal, or
              unenforceable for any reason, such provision shall be eliminated
              or limited to the minimum extent such that the remaining
              provisions of the Terms will continue in full force and effect.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              17. Entire Agreement
            </Heading>
            <Text mb={4}>
              These Terms constitute the entire agreement between you and us
              regarding the Service and supersede all prior and contemporaneous
              written or oral agreements, communications, and other
              understandings relating to the subject matter of these Terms.
            </Text>
          </Box>

          <Box>
            <Heading as="h2" size="lg" mb={4}>
              18. Contact Information
            </Heading>
            <Text mb={4}>
              If you have any questions about these Terms, please contact us at{" "}
              <Link href="mailto:papaandthejimjams@gmail.com" color="blue.500">
                papaandthejimjams@gmail.com
              </Link>
              .
            </Text>
          </Box>

          <Text mb={4}>
            By using Snel, you acknowledge that you have read these Terms,
            understand them, and agree to be bound by them.
          </Text>
        </VStack>
      </Container>
      <Footer />
    </>
  );
}
