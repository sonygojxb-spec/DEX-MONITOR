> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# S3 Bucket Setup

This is a comprehensive step-by-step walkthrough on how to set up an AWS S3 bucket for your Datashare exports.

What is Amazon S3?

* [https://www.youtube.com/watch?v=ecv-19sYL3w](https://www.youtube.com/watch?v=ecv-19sYL3w)

**Account Setup**

1. Login into the AWS console / create an Amazon S3 Cloud Objective Storage account here with your IAM user ID or Root User Email: [https://aws.amazon.com/s3/](https://aws.amazon.com/s3/)
   * Note: AWS may require you to have a 2 Factor Authentication method when creating an account. You can download Google Auth or similar to satisfy this account creation requirement

**Creating an S3 Storage Bucket**

2. After you have successfully signed into your account, naviagete to Amazon S3
3. Click the Create bucket button:

   <Frame>
     <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at12.19.45PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=e3b1b13cdea844e253328a1104c01701" alt="Screenshot 2026 03 09 At 12 19 45 PM" width="1806" height="558" data-path="images/Screenshot2026-03-09at12.19.45PM.png" />
   </Frame>
4. When configuring the storage bucket follow these setup steps below:

* General configuration = General Purpose
* Bucket name = anything you want, example: "moralis-datashare-bucket"

<Frame>
  <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at12.28.20PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=51bcf2088ba3f181a442037d4ada6d03" alt="Screenshot 2026 03 09 At 12 28 20 PM" width="2472" height="750" data-path="images/Screenshot2026-03-09at12.28.20PM.png" />
</Frame>

5. Objective Ownership = ACLs disabled (recommended)

   <Frame>
     <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at12.32.21PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=69ac2cc091814669717eeb38ff6119a9" alt="Screenshot 2026 03 09 At 12 32 21 PM" width="1872" height="394" data-path="images/Screenshot2026-03-09at12.32.21PM.png" />
   </Frame>
6. Block Public Access settings for this bucket = True

   <Frame>
     <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at12.36.59PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=d502ffb7c5771e535fdbe8f57640a076" alt="Screenshot 2026 03 09 At 12 36 59 PM" width="2440" height="556" data-path="images/Screenshot2026-03-09at12.36.59PM.png" />
   </Frame>
7. Bucket Versioning = Disabled

   <Frame>
     <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at12.40.08PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=a1fe424bd0eef24ba8d1789007a4fbe7" alt="Screenshot 2026 03 09 At 12 40 08 PM" width="2428" height="280" data-path="images/Screenshot2026-03-09at12.40.08PM.png" />
   </Frame>
8. Tags are optional. Skip or include tags.
9. Default encryption = Keep SSE-S3 selected and Enable Bucket Key

   <Frame>
     <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at12.42.18PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=f12cfeda5db4ec0284d2292f86ae3adb" alt="Screenshot 2026 03 09 At 12 42 18 PM" width="1570" height="468" data-path="images/Screenshot2026-03-09at12.42.18PM.png" />
   </Frame>
10. Click Create Bucket

**Create a Bucket Policy with IAM user**

11. In the Searchbar type "IAM" and select "IAM Manage access to AWS resources"

    * You will be brought to the IAM Dashboard if you are logged in.

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.09.53PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=8bd44bfa8045a02bcb27f8c53b66ed18" alt="Screenshot 2026 03 09 At 1 09 53 PM" width="1712" height="326" data-path="images/Screenshot2026-03-09at1.09.53PM.png" />
    </Frame>
12. On the left sidebar under Access Management, click "Users"

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.20.55PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=f4ff26ab45338f08fa1301f17002103e" alt="Screenshot 2026 03 09 At 1 20 55 PM" width="350" height="148" data-path="images/Screenshot2026-03-09at1.20.55PM.png" />
    </Frame>
13. Click the "Create user" button.

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.21.43PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=6823908fd887671e2abcaff7fd5fe2f2" alt="Screenshot 2026 03 09 At 1 21 43 PM" width="230" height="88" data-path="images/Screenshot2026-03-09at1.21.43PM.png" />
    </Frame>
14. Set the user name, example = "moralis-datashare-bucket-user"
    * Leave unchecked "Provide user access to the AWS Management Console"
    * Click Next

      <Frame>
        <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.24.09PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=8f79463dac32aada25dc26d76ae929c5" alt="Screenshot 2026 03 09 At 1 24 09 PM" width="1990" height="662" data-path="images/Screenshot2026-03-09at1.24.09PM.png" />
      </Frame>
15. Click "Attach policies directly". This is the best approach for a single-purpose user.
16. In the Seachbar type "S3Full" and click Next.

    <Frame>
      <Frame>
        <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.29.20PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=667afecf493e85e7177f8f8b7900946b" alt="Screenshot 2026 03 09 At 1 29 20 PM" width="1840" height="516" data-path="images/Screenshot2026-03-09at1.29.20PM.png" />
      </Frame>
    </Frame>
17. Click "Create user".

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.30.02PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=703bc484aaed90eb043649ace6a622c3" alt="Screenshot 2026 03 09 At 1 30 02 PM" width="2196" height="864" data-path="images/Screenshot2026-03-09at1.30.02PM.png" />

      <Frame>
        <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.31.02PM-1.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=b3a17d6f39998c9a32093d8141aaeb83" alt="Screenshot 2026 03 09 At 1 31 02 PM" width="1092" height="162" data-path="images/Screenshot2026-03-09at1.31.02PM-1.png" />
      </Frame>
    </Frame>

**Access Keys**

18. Next, you need to create Access Keys for this IAM user.

    * Click on your username, example: "moralis-datashare-bucket-user" then go to the "Security credentials" tab.

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.41.50PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=7b9700679912eaad7da2aa62a0f48db9" alt="Screenshot 2026 03 09 At 1 41 50 PM" width="836" height="80" data-path="images/Screenshot2026-03-09at1.41.50PM.png" />
    </Frame>

    * Scroll down on this page, you'll see an "Access keys" section with a "Create access key" button. Click that.

      <Frame>
        <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.42.55PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=4442c91643f9ca8d6705079059eadf6a" alt="Screenshot 2026 03 09 At 1 42 55 PM" width="2130" height="248" data-path="images/Screenshot2026-03-09at1.42.55PM.png" />
      </Frame>
    * Select "Third-party service" — since Moralis Datashare is an external service that will write to your S3 bucket. Then click "Next".

      <Frame>
        <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.44.15PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=1acba5032c9991465cb13ed0c6c476ee" alt="Screenshot 2026 03 09 At 1 44 15 PM" width="1458" height="618" data-path="images/Screenshot2026-03-09at1.44.15PM.png" />
      </Frame>
    * Set description tab, example: "Moralis Datashare S3 export" then click Create access key.
    * You're key has been created.

      <Frame>
        <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.47.40PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=befdb15ea2cda45ded3a5f4029341183" alt="Screenshot 2026 03 09 At 1 47 40 PM" width="1434" height="66" data-path="images/Screenshot2026-03-09at1.47.40PM.png" />
      </Frame>

**Moralis Datashare Dashboard - Configuration**

19. Navigate to the Moralis Datashare Dashboard by clicking on the Create Export button. [https://moralis.com/](https://moralis.com/)

<Frame>
  <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.50.01PM-2.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=202665af8d129843942667825e449f10" alt="Screenshot 2026 03 09 At 1 50 01 PM" width="1063" height="34" data-path="images/Screenshot2026-03-09at1.50.01PM-2.png" />
</Frame>

20. Select the chain and data types that you want to fetch bulk blockchain data for.

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.58.08PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=a7ff4fe35a242fb0c8969f6d96e6f576" alt="Screenshot 2026 03 09 At 1 58 08 PM" width="420" height="948" data-path="images/Screenshot2026-03-09at1.58.08PM.png" />
    </Frame>
21. Set your date range

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at1.59.30PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=54142a84d07efda911d7eb28090ed3dc" alt="Screenshot 2026 03 09 At 1 59 30 PM" width="846" height="252" data-path="images/Screenshot2026-03-09at1.59.30PM.png" />
    </Frame>
22. Add a Wallet or Token Address

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at2.02.46PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=6c31e4d1843e642a6013caead48ef6d9" alt="Screenshot 2026 03 09 At 2 02 46 PM" width="858" height="370" data-path="images/Screenshot2026-03-09at2.02.46PM.png" />
    </Frame>
23. Set a Destination and Output format

    <Frame>
      <img src="https://mintcdn.com/moralis/doRskAvQ2QsOeJg5/images/Screenshot2026-03-09at2.03.38PM.png?fit=max&auto=format&n=doRskAvQ2QsOeJg5&q=85&s=207c56736ce3f4bd6792001dedf08c6d" alt="Screenshot 2026 03 09 At 2 03 38 PM" width="508" height="432" data-path="images/Screenshot2026-03-09at2.03.38PM.png" />
    </Frame>

* Add new S3 compadible storage destination for the export - input your S3 Keys here.

  <Frame>
    <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at2.04.24PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=42a6bda170a69750c32c85792ad4482b" alt="Screenshot 2026 03 09 At 2 04 24 PM" width="854" height="148" data-path="images/Screenshot2026-03-09at2.04.24PM.png" />
  </Frame>

<Frame>
  <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at2.07.50PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=e486a3e5ce60b31082920453eecbc74c" alt="Screenshot 2026 03 09 At 2 07 50 PM" width="806" height="1012" data-path="images/Screenshot2026-03-09at2.07.50PM.png" />
</Frame>

24. Select Destination.

<Frame>
  <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at2.09.12PM-2.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=f98e4e5bcac7550a1548e6b91fee2805" alt="Screenshot 2026 03 09 At 2 09 12 PM" width="542" height="218" data-path="images/Screenshot2026-03-09at2.09.12PM-2.png" />
</Frame>

25. Click "Estimate" to view the required GB for your export.

    <Frame>
      <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/Screenshot2026-03-09at2.10.46PM.png?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=de32eb4484160a7cadab68cdd935607a" alt="Screenshot 2026 03 09 At 2 10 46 PM" width="852" height="166" data-path="images/Screenshot2026-03-09at2.10.46PM.png" />
    </Frame>

**Complete - You can now export Bulk Blockchain Data with Moralis Datashare!**

<Frame>
  <img src="https://mintcdn.com/moralis/5-RjbdiAMQyRzkiU/images/youdidit-1.webp?fit=max&auto=format&n=5-RjbdiAMQyRzkiU&q=85&s=07801bd92c9efb7bf1175b5191abc29d" alt="You Did It" width="641" height="360" data-path="images/youdidit-1.webp" />
</Frame>
